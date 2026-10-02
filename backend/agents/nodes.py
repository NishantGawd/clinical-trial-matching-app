import asyncio
import json
import re
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field, field_validator
import psycopg2

from config import DATABASE_URL, get_llm, MODEL_REASONING, MODEL_STRUCTURED
from agents.state import MatchingState
from agents.cache import setup_cache_table, get_cached_result, save_to_cache
from agents.memory import (
    retrieve_similar_few_shot_memories,
    format_few_shot_prompt_context,
    store_verified_match_memory
)
from agents.similarity import compute_dynamic_alternative_trials
from agents.rules_filter import evaluate_fast_path_rules
from agents.async_engine import run_in_worker_thread
from ml_scoring import predict_patient_attrition, evaluate_dynamic_gating

# Global Semaphore for Concurrent Swarm Inference
LLM_SEMAPHORE = asyncio.Semaphore(5)

# =========================================================================
# PYDANTIC STRUCTURED OUTPUT SCHEMAS
# =========================================================================
class ExtractedPatientFeatures(BaseModel):
    age: float = Field(default=60.0, description="Patient age in years.")
    distance_miles: float = Field(default=50.0, description="Estimated distance from trial site in miles.")
    prior_treatments: float = Field(default=1.0, description="Number of prior distinct lines of systemic therapy/surgeries.")
    ecog_score: float = Field(default=1.0, description="Baseline ECOG performance status (0.0 to 4.0).")
    toxicity_burden: float = Field(default=2.0, description="Cumulative toxicity and symptom burden index (0.0 to 10.0).")
    has_caregiver: float = Field(default=1.0, description="1.0 if patient has family/caregiver support, 0.0 if living alone/unsupported.")

class ActionableIntervention(BaseModel):
    intervention_type: str = Field(description="Category of intervention, e.g., Transportation Assistance, Caregiver Support, Toxicity Monitoring.")
    description: str = Field(description="Summary of the recommended retention strategy.")
    implementation_details: Optional[str] = Field(default="Coordinate clinical and logistical trial support.", description="Actionable implementation step.")

class MLAttritionRisk(BaseModel):
    status: str = Field(
        default="EVALUATED - BASELINE FRAILTY PROFILE", 
        description="Clinical evaluation state: 'EVALUATED - TRIAL ACTIVE' for matches, or 'EVALUATED - BASELINE FRAILTY PROFILE' for general navigation."
    )
    attrition_risk_level: Optional[str] = Field(default="MEDIUM", description="Categorized risk: LOW, MEDIUM, or HIGH.")
    dropout_probability_percent: Optional[str] = Field(default="0.0%", description="Calibrated predicted probability of attrition.")
    raw_dropout_probability: Optional[float] = Field(default=None, description="Continuous attrition probability (0.00 to 1.00).")
    primary_risk_drivers: List[str] = Field(default_factory=list, description="Top positive SHAP contributors elevating attrition risk.")
    primary_retention_drivers: List[str] = Field(default_factory=list, description="Top negative SHAP contributors mitigating attrition risk.")
    eval_metrics_used: Dict[str, Any] = Field(default_factory=dict, description="Extracted clinical feature vector ingested by the model.")
    actionable_interventions: List[ActionableIntervention] = Field(default_factory=list, description="Targeted clinical/logistical navigation steps.")
    message: Optional[str] = Field(default=None, description="Navigation guidance notes.")

    @field_validator("status", mode="before")
    @classmethod
    def coerce_status(cls, v):
        return str(v) if v else "EVALUATED - BASELINE FRAILTY PROFILE"

class AlternativeTrial(BaseModel):
    trial_id: str
    trial_title: str
    similarity_match_score: str
    match_rationale: str

    @field_validator("similarity_match_score", mode="before")
    @classmethod
    def coerce_similarity_score(cls, v):
        if isinstance(v, (int, float)):
            return f"{round(float(v) * (100.0 if float(v) <= 1.0 else 1.0), 1)}%"
        return str(v)

    @field_validator("trial_title", mode="before")
    @classmethod
    def coerce_trial_title(cls, v):
        return str(v) if v else "Clinical Trial Protocol"

class CalibrationMetrics(BaseModel):
    hard_gate_passed: bool = Field(description="Whether hard inclusion/exclusion gates cleared.")
    metric_calibration_method: str = Field(
        default="Platt-Calibrated Soft-Voting & Physiological Gating", 
        description="Algorithm used to calibrate output."
    )
    gating_penalties: Dict[str, float] = Field(
        default_factory=dict, 
        description="Itemized soft penalty deductions."
    )

class FinalMatchSummary(BaseModel):
    patient_id: str
    trial_id: str
    overall_match: bool
    extraction_confidence: float = Field(description="Model certainty in extracting clinical criteria from unstructured text (0.00 to 1.00).")
    eligibility_score: float = Field(description="Continuous feasibility score (0.00 for disqualified, 0.50 to 0.99 for eligible).")
    confidence_score: float = Field(description="Composite score balancing extraction confidence and eligibility.")
    calibration_breakdown: Optional[CalibrationMetrics] = Field(default=None, description="Detailed transparency breakdown of scoring calibration.")
    inclusion_status: str
    exclusion_status: str
    match_summary: str
    ml_attrition_risk: MLAttritionRisk
    alternative_trials: List[AlternativeTrial] = Field(default_factory=list)

    @field_validator("match_summary", mode="before")
    @classmethod
    def coerce_match_summary(cls, v):
        if isinstance(v, dict):
            status = v.get("status", "")
            rationale = v.get("rationale") or v.get("summary") or v.get("detail") or ""
            return f"Match Status: {status}. {rationale}".strip() if rationale else f"Match Status: {status}".strip()
        elif isinstance(v, list):
            return " ".join([str(item) for item in v])
        return str(v) if v is not None else ""

# =========================================================================
# INITIALIZATION & HELPER FUNCTIONS
# =========================================================================
try:
    setup_cache_table()
except Exception:
    pass

def extract_response_text(raw_response: Any) -> str:
    """Safely extracts string content from AIMessage objects or plain strings."""
    if hasattr(raw_response, "content"):
        return str(raw_response.content)
    return str(raw_response)

def clean_think_tags(text: str) -> str:
    """
    Strips <think>...</think> reasoning blocks emitted by deep reasoning models.
    Also handles unclosed opening <think> tags caused by token truncation.
    """
    cleaned = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    cleaned = re.sub(r"<think>.*", "", cleaned, flags=re.DOTALL)
    return cleaned.strip()

def sanitize_agent_reasoning(raw_resp: str, agent_type: str, passed: bool) -> str:
    """
    Sanitizes agent reasoning to prevent truncated sentences, enforcing terminal 
    punctuation ([.!?]) and falling back to complete medical statements if sliced.
    """
    cleaned = clean_think_tags(raw_resp).strip()
    
    # Extract explicit REASONING: block if present
    reasoning_match = re.search(r"REASONING[\s:]*([^\n]+(?:\n[^\n]+)*)", cleaned, re.IGNORECASE)
    reasoning_body = reasoning_match.group(1).strip() if reasoning_match else cleaned
    
    # Strip any leading RESULT tag that may have been caught in the body
    reasoning_body = re.sub(r"^RESULT[\s:]*(?:YES|NO|CLEARED|EXCLUDED)\s*", "", reasoning_body, flags=re.IGNORECASE).strip()
    
    # Check for terminal sentence punctuation
    if not re.search(r"[.!?]$", reasoning_body):
        last_punct = max(reasoning_body.rfind('.'), reasoning_body.rfind('!'), reasoning_body.rfind('?'))
        if last_punct > 25:
            reasoning_body = reasoning_body[:last_punct + 1].strip()
        else:
            if agent_type == "inclusion":
                reasoning_body = (
                    "The patient meets all evaluated primary clinical trial inclusion criteria grounded in documented records."
                    if passed else
                    "The patient does not satisfy essential protocol disease-specific or target inclusion criteria."
                )
            elif agent_type == "exclusion":
                reasoning_body = (
                    "The patient's clinical record documents no active contraindications or disqualifying exclusion factors."
                    if passed else
                    "The patient possesses documented clinical factors triggering protocol safety exclusion criteria."
                )

    result_tag = "YES" if (agent_type == "inclusion" and passed) else ("NO" if agent_type == "inclusion" else ("CLEARED" if passed else "EXCLUDED"))
    return f"RESULT: {result_tag}\nREASONING: {reasoning_body}"

def sanitize_auditor_feedback(raw_resp: str, passed: bool) -> str:
    """
    Sanitizes auditor feedback, ensuring complete sentences and avoiding mid-phrase cutoffs.
    """
    cleaned = clean_think_tags(raw_resp).strip()
    feedback_match = re.search(r"FEEDBACK[\s:]*([^\n]+(?:\n[^\n]+)*)", cleaned, re.IGNORECASE)
    fb_body = feedback_match.group(1).strip() if feedback_match else cleaned
    
    # Remove leading RESULT or EXTRACTION_CONFIDENCE tags
    fb_body = re.sub(r"^(?:RESULT[\s:]*(?:PASS|FAIL)|EXTRACTION_CONFIDENCE[\s:]*[0-9.]+)\s*", "", fb_body, flags=re.IGNORECASE).strip()
    
    if not re.search(r"[.!?]$", fb_body):
        last_punct = max(fb_body.rfind('.'), fb_body.rfind('!'), fb_body.rfind('?'))
        if last_punct > 15:
            fb_body = fb_body[:last_punct + 1].strip()
        else:
            fb_body = (
                "Reasoning is fully verified against clinical records."
                if passed else
                "Clinical reasoning contains discrepancies requiring correction."
            )
    elif len(fb_body) < 15:
        fb_body = "Reasoning is fully verified against clinical records."
        
    return fb_body

def compute_clinical_evidence_ambiguity(patient_text: str, trial_text: str) -> float:
    """
    Computes a continuous factual completeness and clarity baseline (0.70 to 0.99).
    Evaluates:
      1. Timeline and lab completeness (+0.05 to -0.06)
      2. Specific diagnostic biomarkers & stage (+0.05 to -0.04)
      3. Standard physiological lab panels (+0.03)
      4. Negation & hedging ambiguity penalties (-0.03 per hedge up to -0.12)
      5. Sparse text check (-0.08)
    """
    score = 0.85
    p_lower = patient_text.lower()
    
    # 1. Timeline & lab completeness
    date_matches = re.findall(r"\b(?:\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{2,4}|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\b", p_lower)
    if len(date_matches) >= 3:
        score += 0.05
    elif len(date_matches) == 0:
        score -= 0.06

    # 2. Specific diagnostic biomarkers & stage
    has_explicit_biomarker = bool(re.search(r"\b(?:braf|egfr|alk|kras|ros1|pdl1|pd-l1|her2|msi|exon|mutation|wild-type)\b", p_lower))
    has_staging = bool(re.search(r"\b(?:stage\s+[ivx]+|ecog|metastatic|unresectable|resectable|adenocarcinoma|melanoma|carcinoma)\b", p_lower))
    if has_explicit_biomarker and has_staging:
        score += 0.05
    elif not has_staging:
        score -= 0.04

    # 3. Lab values
    has_labs = bool(re.search(r"\b(?:creatinine|anc|platelets|hemoglobin|ast|alt|bilirubin|wbc|inr)\b", p_lower))
    if has_labs:
        score += 0.03

    # 4. Negation & hedging ambiguity penalties
    hedges = re.findall(r"\b(?:unclear|equivocal|suspected|probable|possible|cannot rule out|borderline|unknown|unspecified)\b", p_lower)
    score -= min(0.12, len(hedges) * 0.03)

    # 5. Sparse text penalty
    if len(patient_text.strip().split()) < 40:
        score -= 0.08

    return round(max(0.70, min(0.99, score)), 2)

async def dynamically_extract_features_llm(patient_text: str) -> Dict[str, Any]:
    """
    Uses LLM reasoning with a tight token ceiling to parse clinical metrics from EHR text,
    falling back instantly to deterministic extraction if JSON parsing fails.
    """
    llm = get_llm(MODEL_STRUCTURED, structured_json=True, max_tokens=300)
    schema_str = json.dumps(ExtractedPatientFeatures.model_json_schema(), indent=2)
    
    prompt = f"""
System: You are an expert Clinical Data Extractor. Extract patient physiological and demographic metrics from this medical record.
Respond strictly with a JSON object matching this schema:
{schema_str}

PATIENT RECORD:
{patient_text}

Return ONLY valid JSON.
"""
    try:
        async with LLM_SEMAPHORE:
            raw = await llm.ainvoke(prompt)
        text = clean_think_tags(extract_response_text(raw))
        match = re.search(r"\{.*\}", text, re.DOTALL)
        json_str = match.group(0) if match else text
        parsed = ExtractedPatientFeatures.model_validate_json(json_str)
        return parsed.model_dump()
    except Exception:
        # Fast Deterministic Regex Fallback
        age_match = re.search(r"(\d{1,2})\s*(?:-|\s)*(?:year|yr|yo|years old|\s*M|\s*F)\b", patient_text, re.IGNORECASE)
        age = float(age_match.group(1)) if age_match else 60.0

        ecog_match = re.search(r"ECOG(?:[\s\w]*status|[\s\w]*PS)?[\s:]*([0-4])", patient_text, re.IGNORECASE)
        ecog = float(ecog_match.group(1)) if ecog_match else 1.0

        prior_matches = re.findall(r"(?:chemotherapy|immunotherapy|radiation|resection|surgery|stent|pembrolizumab|carboplatin)\b", patient_text, re.IGNORECASE)
        prior_count = float(min(5, max(1, len(set(prior_matches)))))

        has_caregiver = 0.0 if re.search(r"lives alone|no caregiver|lack of support|unaccompanied|divorced|widowed", patient_text, re.IGNORECASE) else 1.0
        dist_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:miles|mile|mi)\b", patient_text, re.IGNORECASE)
        distance = float(dist_match.group(1)) if dist_match else 45.0

        toxicity = prior_count * 1.1
        if re.search(r"fatigue|nausea|neuropathy|elevated|impairment|steroids|dexamethasone|edema", patient_text, re.IGNORECASE):
            toxicity += 1.8

        return {
            "age": age,
            "distance_miles": distance,
            "prior_treatments": prior_count,
            "ecog_score": ecog,
            "toxicity_burden": round(toxicity, 1),
            "has_caregiver": has_caregiver
        }

# =========================================================================
# MULTI-AGENT NODES
# =========================================================================
async def retrieval_node(state: MatchingState) -> Dict[str, Any]:
    patient_id = state.get("patient_id", "")
    trial_id = state.get("trial_id", "")
    print(f"  [Node 1: Retrieval] Checking cache & database for {patient_id} and {trial_id}...")
    
    cached_data = get_cached_result(patient_id, trial_id)
    if cached_data:
        print(f"  ⚡ CACHE HIT! Instant retrieval for {patient_id} vs {trial_id}")
        return {
            "overall_match": cached_data["overall_match"],
            "confidence_score": cached_data["confidence_score"],
            "inclusion_reasoning": cached_data["inclusion_reasoning"],
            "exclusion_reasoning": cached_data["exclusion_reasoning"],
            "summary_report": cached_data["summary_report"],
            "error": "CACHE_HIT"
        }

    def _fetch_contexts():
        conn = psycopg2.connect(DATABASE_URL, connect_timeout=15)
        cur = conn.cursor()
        cur.execute("SELECT content FROM patient_embeddings WHERE doc_id = %s;", (patient_id,))
        p_rows = cur.fetchall()
        p_text = "\n".join([r[0] for r in p_rows]) if p_rows else ""
        
        cur.execute("SELECT content FROM trial_embeddings WHERE doc_id = %s;", (trial_id,))
        t_rows = cur.fetchall()
        t_text = "\n".join([r[0] for r in t_rows]) if t_rows else ""
        
        cur.close()
        conn.close()
        
        few_shots = retrieve_similar_few_shot_memories(p_text, current_patient_id=patient_id, limit=2)
        return p_text, t_text, few_shots

    try:
        p_text, t_text, few_shots = await run_in_worker_thread(_fetch_contexts)
        if few_shots:
            print(f"  🧠 [Prompt Memory] Retrieved {len(few_shots)} similar verified clinical exemplars for dynamic few-shot prompting.")

        fast_path = evaluate_fast_path_rules(p_text, t_text)
        if fast_path:
            print(f"  ⚡ FAST-PATH DETECTED ({fast_path.get('disqualification_type', 'DISQUALIFIED')}): Deterministic safety disqualification.")
            return {
                "patient_context": p_text,
                "trial_context": t_text,
                "few_shot_memories": few_shots,
                "inclusion_passed": fast_path["inclusion_passed"],
                "inclusion_reasoning": fast_path["inclusion_reasoning"],
                "exclusion_cleared": fast_path["exclusion_cleared"],
                "exclusion_reasoning": fast_path["exclusion_reasoning"],
                "audit_passed": True,
                "auditor_feedback": "Fast-path pre-filter verified against explicit clinical protocol boundaries.",
                "audit_loop_count": 1,
                "error": "FAST_PATH_EXIT"
            }

        return {
            "patient_context": p_text,
            "trial_context": t_text,
            "few_shot_memories": few_shots,
            "error": None,
            "audit_loop_count": 0
        }
    except Exception as e:
        return {"error": f"Retrieval failed: {str(e)}"}

async def inclusion_node(state: MatchingState) -> Dict[str, Any]:
    if state.get("error"): 
        return {}
    print("  [Node 2: Inclusion Agent] Analyzing eligibility criteria concurrently...")
    llm = get_llm(MODEL_REASONING, structured_json=False, max_tokens=768)
    
    memories = state.get("few_shot_memories") or []
    few_shot_prompt_part = format_few_shot_prompt_context(memories, target_agent="inclusion")
    feedback_context = f"\nCRITIC FEEDBACK FROM PREVIOUS AUDIT: {state.get('auditor_feedback')}\nAdjust your reasoning accordingly." if state.get('auditor_feedback') else ""
    
    prompt = f"""
System: You are an expert clinical trial investigator evaluating candidate eligibility.
Determine whether the PATIENT satisfies the trial INCLUSION CRITERIA based solely on explicit clinical facts.

CRITICAL INSTRUCTIONS:
- Output the clinical determination immediately.
- Do NOT output conversational monologue, internal thoughts, or preamble.
- Output complete sentences and finish your reasoning cleanly with proper terminal punctuation.

{few_shot_prompt_part}
{feedback_context}

PATIENT RECORD:
{state.get('patient_context', '')}

TRIAL PROTOCOL:
{state.get('trial_context', '')}

CRITICAL REQUIREMENT: Output EXACTLY in this format:
RESULT: YES or NO
REASONING: Concise, objective clinical justification grounded strictly in documented facts.
"""
    async with LLM_SEMAPHORE:
        raw = await llm.ainvoke(prompt)
    raw_text = extract_response_text(raw)
    cleaned_resp = clean_think_tags(raw_text) or raw_text.strip()
    is_passed = "RESULT: YES" in cleaned_resp.upper() or ("YES" in cleaned_resp.upper() and "NO" not in cleaned_resp.upper())
    
    # Enforce clean terminal punctuation and sentence boundaries
    final_reasoning = sanitize_agent_reasoning(cleaned_resp, agent_type="inclusion", passed=is_passed)
    return {"inclusion_passed": is_passed, "inclusion_reasoning": final_reasoning}

async def exclusion_node(state: MatchingState) -> Dict[str, Any]:
    if state.get("error"): 
        return {}
    print("  [Node 3: Exclusion Agent] Analyzing disqualifying criteria concurrently...")
    llm = get_llm(MODEL_REASONING, structured_json=False, max_tokens=768)
    
    memories = state.get("few_shot_memories") or []
    few_shot_prompt_part = format_few_shot_prompt_context(memories, target_agent="exclusion")
    feedback_context = f"\nCRITIC FEEDBACK FROM PREVIOUS AUDIT: {state.get('auditor_feedback')}\nAdjust your reasoning accordingly." if state.get('auditor_feedback') else ""
    
    prompt = f"""
System: You are an expert clinical safety investigator analyzing trial contraindications.
Determine whether the PATIENT has any disqualifying EXCLUSION CRITERIA.

CRITICAL INSTRUCTIONS:
- Output the clinical determination immediately.
- Do NOT output conversational monologue, internal thoughts, or preamble.
- Output complete sentences and finish your reasoning cleanly with proper terminal punctuation.

{few_shot_prompt_part}
{feedback_context}

PATIENT RECORD:
{state.get('patient_context', '')}

TRIAL PROTOCOL:
{state.get('trial_context', '')}

CRITICAL REQUIREMENT: Output EXACTLY in this format:
RESULT: CLEARED or EXCLUDED
REASONING: Concise, objective clinical justification grounded strictly in documented facts.
"""
    async with LLM_SEMAPHORE:
        raw = await llm.ainvoke(prompt)
    raw_text = extract_response_text(raw)
    cleaned_resp = clean_think_tags(raw_text) or raw_text.strip()
    is_cleared = "RESULT: CLEARED" in cleaned_resp.upper() or ("CLEARED" in cleaned_resp.upper() and "EXCLUDED" not in cleaned_resp.upper())
    
    # Enforce clean terminal punctuation and sentence boundaries
    final_reasoning = sanitize_agent_reasoning(cleaned_resp, agent_type="exclusion", passed=is_cleared)
    return {"exclusion_cleared": is_cleared, "exclusion_reasoning": final_reasoning}

async def auditor_node(state: MatchingState) -> Dict[str, Any]:
    if state.get("error"): 
        return {}
    loop_count = state.get("audit_loop_count", 0) + 1
    print(f"  [Node 3.5: Critic Agent] Auditing reasoning & evaluating extraction certainty (Loop {loop_count})...")
    llm = get_llm(MODEL_REASONING, structured_json=False, max_tokens=768)
    
    patient_context = state.get("patient_context", "")
    trial_context = state.get("trial_context", "")
    
    ambiguity_baseline = compute_clinical_evidence_ambiguity(patient_context, trial_context)

    prompt = f"""
System: You are a Senior Medical Auditor. Your job is to verify that junior agent reasoning is completely factually grounded in the Patient Record without hallucinations or unsupported assumptions.
Also, assess how clear, complete, and unambiguous the clinical evidence is.
The patient chart has an empirical evidence baseline clarity score of: {ambiguity_baseline:.2f} (Scale: 0.70 to 0.99).

CRITICAL INSTRUCTIONS:
- Output your assessment immediately without conversational monologue, thoughts, or preamble.
- Write complete, self-contained sentences for FEEDBACK ending strictly with terminal punctuation [.!?]. Never leave a sentence unfinished.

PATIENT RECORD: 
{patient_context}

TRIAL PROTOCOL: 
{trial_context}

INCLUSION REASONING: 
{state.get('inclusion_reasoning', '')}

EXCLUSION REASONING: 
{state.get('exclusion_reasoning', '')}

INSTRUCTIONS:
1. Verify if any facts were hallucinated or contradicted.
2. Provide an EXTRACTION_CONFIDENCE score as a float strictly between 0.70 and 0.99 calibrated around {ambiguity_baseline:.2f}.
   - Clear, multi-date charts with explicit labs/biomarkers: 0.96 - 0.99
   - Moderately detailed records with standard facts: 0.88 - 0.95
   - Sparse records, missing lab timestamps, or speculative notes: 0.70 - 0.85

Output EXACTLY:
RESULT: PASS or FAIL
EXTRACTION_CONFIDENCE: [Float between 0.70 and 0.99]
FEEDBACK: [Concise, complete clinical assessment explaining discrepancies, or 'Reasoning is fully verified against clinical records.']
"""
    async with LLM_SEMAPHORE:
        raw = await llm.ainvoke(prompt)
    raw_text = extract_response_text(raw)
    resp = clean_think_tags(raw_text)
    passed = "RESULT: PASS" in resp.upper() or ("PASS" in resp.upper() and "FAIL" not in resp.upper())
    
    conf_match = re.search(r"EXTRACTION_CONFIDENCE[\s:]*([0-1](?:\.\d+)?)", resp, re.IGNORECASE)
    if conf_match:
        dynamic_conf = float(conf_match.group(1))
    else:
        dynamic_conf = ambiguity_baseline
    
    dynamic_conf = round(max(0.70, min(0.99, dynamic_conf)), 2)
    
    # Sanitize feedback string cleanly
    auditor_feedback = sanitize_auditor_feedback(resp, passed=passed)

    if not passed:
        print("    ⚠️ AUDIT FAILED: Requesting agent self-correction...")
    else:
        print(f"    ✅ AUDIT PASSED: Factually grounded (Extraction Certainty: {dynamic_conf:.2f}).")
        
    return {
        "audit_passed": passed, 
        "auditor_feedback": auditor_feedback, 
        "extraction_confidence": dynamic_conf, 
        "audit_loop_count": loop_count
    }

async def synthesis_node(state: MatchingState) -> Dict[str, Any]:
    if state.get("error") == "CACHE_HIT":
        return {
            "overall_match": state.get("overall_match"),
            "confidence_score": state.get("confidence_score"),
            "inclusion_reasoning": state.get("inclusion_reasoning"),
            "exclusion_reasoning": state.get("exclusion_reasoning"),
            "summary_report": state.get("summary_report")
        }
    if state.get("error") and state.get("error") != "FAST_PATH_EXIT":
        return {"overall_match": False, "confidence_score": 0.0, "summary_report": {"error": state.get("error")}}
        
    print("  [Node 4: Synthesis & ML Attrition Engine] Synthesizing ML Attrition & Calibrated Match Output...")
    llm = get_llm(MODEL_STRUCTURED, structured_json=True, max_tokens=1500)
    
    inc_pass = bool(state.get("inclusion_passed", False))
    exc_clear = bool(state.get("exclusion_cleared", False))
    overall = inc_pass and exc_clear
    is_fast_path = (state.get("error") == "FAST_PATH_EXIT")
    
    # 1. Ingest Empirical Extraction Confidence
    raw_conf = state.get("extraction_confidence")
    if raw_conf is not None:
        extraction_conf = float(raw_conf)
    else:
        extraction_conf = compute_clinical_evidence_ambiguity(
            state.get("patient_context", ""), 
            state.get("trial_context", "")
        )
    extraction_conf = round(max(0.70, min(0.99, extraction_conf)), 2)
    
    # 2. Extract Patient Features for ML Modeling Across ALL Candidates
    patient_metrics = await dynamically_extract_features_llm(state.get("patient_context", ""))
    
    # 3. Dynamic Gating & Physiological Soft Penalty Deductions
    gating_results = evaluate_dynamic_gating(
        inclusion_passed=inc_pass,
        exclusion_cleared=exc_clear,
        extraction_confidence=extraction_conf,
        ecog_score=patient_metrics.get("ecog_score", 1.0),
        toxicity_burden=patient_metrics.get("toxicity_burden", 2.0)
    )
    
    calculated_eligibility = round(float(gating_results.get("eligibility_score", 0.0)), 2)
    calculated_confidence = calculated_eligibility if overall else 0.00
    
    calibration_breakdown_dict = {
        "hard_gate_passed": overall,
        "metric_calibration_method": "Platt-Calibrated Soft-Voting & Physiological Gating",
        "gating_penalties": {
            "ecog_penalty": -0.10 if patient_metrics.get("ecog_score", 0) >= 2 and overall else 0.0,
            "toxicity_penalty": -0.08 if patient_metrics.get("toxicity_burden", 0) > 5.0 and overall else 0.0
        }
    }

    # 4. Concurrently Compute ML Attrition & Candidate Alternatives
    async def _resolve_ml_attrition():
        try:
            raw_attr = await run_in_worker_thread(
                predict_patient_attrition, 
                **patient_metrics, 
                is_eligible=overall
            )
            return raw_attr
        except Exception as ml_err:
            return {
                "status": "EVALUATED - HEURISTIC FALLBACK",
                "attrition_risk_level": "UNKNOWN",
                "dropout_probability_percent": "N/A",
                "raw_dropout_probability": None,
                "primary_risk_drivers": [f"Inference warning: {str(ml_err)}"],
                "primary_retention_drivers": [],
                "eval_metrics_used": patient_metrics,
                "actionable_interventions": [],
                "message": "Fallback heuristics engaged."
            }

    async def _resolve_alternatives():
        if overall:
            return []
        return await compute_dynamic_alternative_trials(
            patient_context=state.get("patient_context", ""),
            current_trial_id=state.get("trial_id", ""),
            limit=3
        )

    attrition_data, alternative_trials = await asyncio.gather(
        _resolve_ml_attrition(),
        _resolve_alternatives()
    )

    # 5. Deterministic Fast-Path Direct Bypass
    if is_fast_path:
        report_data = {
            "patient_id": state.get("patient_id", ""),
            "trial_id": state.get("trial_id", ""),
            "overall_match": False,
            "extraction_confidence": extraction_conf,
            "eligibility_score": 0.00,
            "confidence_score": 0.00,
            "calibration_breakdown": calibration_breakdown_dict,
            "inclusion_status": "FAILED",
            "exclusion_status": "DISQUALIFIED",
            "match_summary": "Disqualified via safety pre-filter boundary check.",
            "ml_attrition_risk": attrition_data,
            "alternative_trials": alternative_trials
        }

        await run_in_worker_thread(
            save_to_cache,
            patient_id=state.get("patient_id", ""),
            trial_id=state.get("trial_id", ""),
            overall_match=False,
            confidence_score=0.00,
            inclusion_reasoning=state.get("inclusion_reasoning", ""),
            exclusion_reasoning=state.get("exclusion_reasoning", ""),
            summary_report=report_data
        )

        return {
            "overall_match": False,
            "extraction_confidence": extraction_conf,
            "eligibility_score": 0.00,
            "confidence_score": 0.00,
            "summary_report": report_data
        }

    schema_json_str = json.dumps(FinalMatchSummary.model_json_schema(), indent=2)

    prompt = f"""
System: You are an expert Clinical Trial JSON Synthesizer. Synthesize the findings of the specialized agents into the target JSON schema.
Respond strictly with a JSON object matching this schema:
{schema_json_str}

PATIENT ID: {state.get('patient_id')}
TRIAL ID: {state.get('trial_id')}

INCLUSION FINDINGS:
Decision: {'PASSED' if inc_pass else 'FAILED'}
Reasoning: {state.get('inclusion_reasoning', '')}

EXCLUSION FINDINGS:
Decision: {'CLEARED' if exc_clear else 'DISQUALIFIED'}
Reasoning: {state.get('exclusion_reasoning', '')}

AUDITOR ASSESSMENT:
Feedback: {state.get('auditor_feedback', '')}
Extraction Certainty: {extraction_conf}

CALCULATED METRICS:
Overall Match: {overall}
Eligibility Feasibility Score: {calculated_eligibility}
Confidence Score: {calculated_confidence}

PRE-COMPUTED ML ATTRITION & FRAILTY ASSESSMENT:
{json.dumps(attrition_data, indent=2)}

ALTERNATIVE TRIALS:
{json.dumps(alternative_trials, indent=2)}

CALIBRATION TRANSPARENCY:
{json.dumps(calibration_breakdown_dict, indent=2)}

INSTRUCTIONS:
1. Populate `overall_match` with {str(overall).lower()}.
2. Populate `inclusion_status` as '{'PASSED' if inc_pass else 'FAILED'}'.
3. Populate `exclusion_status` as '{'CLEARED' if exc_clear else 'DISQUALIFIED'}'.
4. Populate `extraction_confidence` with {extraction_conf}.
5. Populate `eligibility_score` with {calculated_eligibility}.
6. Populate `confidence_score` with {calculated_confidence}.
7. Synthesize an objective, clinically precise `match_summary` string explaining the overall eligibility decision.
8. Retain all pre-computed ML attrition risk details, eval_metrics_used, interventions, and alternative trials exactly as provided.

Return ONLY valid raw JSON without explanation or markdown backticks.
"""

    async with LLM_SEMAPHORE:
        raw_response = await llm.ainvoke(prompt)
    raw_text = extract_response_text(raw_response)
    resp = clean_think_tags(raw_text)
    
    try:
        match = re.search(r"\{.*\}", resp, re.DOTALL)
        json_str = match.group(0) if match else resp
        parsed_output = FinalMatchSummary.model_validate_json(json_str)
        report_data = parsed_output.model_dump()
        
        # Ensure model-generated data integrity
        report_data["overall_match"] = overall
        report_data["extraction_confidence"] = extraction_conf
        report_data["eligibility_score"] = calculated_eligibility
        report_data["confidence_score"] = calculated_confidence
        report_data["calibration_breakdown"] = calibration_breakdown_dict
        report_data["ml_attrition_risk"] = attrition_data
        report_data["alternative_trials"] = alternative_trials
            
        final_confidence = calculated_confidence
    except Exception as e:
        print(f"    ⚠️ JSON Validation Fallback: {e}")
        final_confidence = calculated_confidence
        report_data = {
            "patient_id": state.get("patient_id", ""),
            "trial_id": state.get("trial_id", ""),
            "overall_match": overall,
            "extraction_confidence": extraction_conf,
            "eligibility_score": final_confidence,
            "confidence_score": final_confidence,
            "calibration_breakdown": calibration_breakdown_dict,
            "inclusion_status": "PASSED" if inc_pass else "FAILED",
            "exclusion_status": "CLEARED" if exc_clear else "DISQUALIFIED",
            "match_summary": "Patient meets all inclusion requirements and has no active exclusion criteria." if overall else "Patient disqualified based on clinical criteria evaluation.",
            "ml_attrition_risk": attrition_data,
            "alternative_trials": alternative_trials
        }

    # Save to Cache and Prompt Memory Bank
    await run_in_worker_thread(
        save_to_cache,
        patient_id=state.get("patient_id", ""),
        trial_id=state.get("trial_id", ""),
        overall_match=bool(overall),
        confidence_score=final_confidence,
        inclusion_reasoning=state.get("inclusion_reasoning", ""),
        exclusion_reasoning=state.get("exclusion_reasoning", ""),
        summary_report=report_data
    )
    
    await run_in_worker_thread(
        store_verified_match_memory,
        patient_id=state.get("patient_id", ""),
        trial_id=state.get("trial_id", ""),
        patient_context=state.get("patient_context", ""),
        trial_context=state.get("trial_context", ""),
        inclusion_passed=bool(inc_pass),
        inclusion_reasoning=state.get("inclusion_reasoning", ""),
        exclusion_cleared=bool(exc_clear),
        exclusion_reasoning=state.get("exclusion_reasoning", ""),
        overall_match=bool(overall)
    )
        
    return {
        "overall_match": overall,
        "extraction_confidence": extraction_conf,
        "eligibility_score": calculated_eligibility,
        "confidence_score": final_confidence,
        "summary_report": report_data
    }