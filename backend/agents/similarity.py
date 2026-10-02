import re
import psycopg2
from typing import List, Dict, Any, Set
from config import DATABASE_URL
from agents.async_engine import run_in_worker_thread, get_async_embedder

KNOWN_BIOMARKERS = {
    "egfr", "braf", "kras", "nras", "alk", "ros1", "ret", "her2", "erbb2",
    "pik3ca", "tp53", "brca1", "brca2", "pd-l1", "pdl1", "msi-h", "dmmr",
    "tmb-h", "claudin", "fgfr", "ntrk", "idh1", "idh2", "cdk4", "cdk6"
}

STAGE_PATTERNS = [
    r"stage\s+i{1,3}[ab]?", r"stage\s+iv[ab]?", r"metastatic", r"resectable",
    r"unresectable", r"locally\s+advanced", r"recurrent", r"refractory"
]

def extract_clinical_entities(text: str) -> Dict[str, Set[str]]:
    """Extracts biomarkers, histology indicators, and staging tokens from raw context."""
    lower_text = text.lower()
    
    found_biomarkers = set()
    for bm in KNOWN_BIOMARKERS:
        if re.search(rf"\b{re.escape(bm)}\b", lower_text):
            found_biomarkers.add(bm)
            
    mutations = re.findall(r"\b(?:v600[ek]|exon\s*\d+|t790m|g12[cda]|l858r)\b", lower_text)
    for m in mutations:
        found_biomarkers.add(re.sub(r"\s+", "", m))

    found_stages = set()
    for sp in STAGE_PATTERNS:
        matches = re.findall(sp, lower_text)
        for match in matches:
            found_stages.add(re.sub(r"\s+", " ", match).strip())

    return {
        "biomarkers": found_biomarkers,
        "stages": found_stages
    }

def calculate_jaccard_similarity(set_a: Set[str], set_b: Set[str]) -> float:
    """Calculates Jaccard similarity index between two entity sets."""
    if not set_a or not set_b:
        return 0.0
    intersection = len(set_a.intersection(set_b))
    union = len(set_a.union(set_b))
    return float(intersection / union) if union > 0 else 0.0

def clean_truncate_title(title: str, max_chars: int = 130) -> str:
    """Cleanly truncates trial titles at word boundaries without cutting words in half."""
    cleaned = re.sub(r"\s+", " ", title).strip()
    if len(cleaned) <= max_chars:
        return cleaned
    truncated = cleaned[:max_chars].rsplit(" ", 1)[0]
    return re.sub(r"[\s,;:.-]+$", "", truncated) + "..."

async def compute_dynamic_alternative_trials(
    patient_context: str,
    current_trial_id: str,
    limit: int = 3
) -> List[Dict[str, Any]]:
    """
    Computes real-time dynamic alternative trial matching using Hybrid 3-Factor Re-Ranking:
    Final Score = 0.50 * DenseVector + 0.30 * BiomarkerScore + 0.20 * StageScore
    """
    def _re_rank_candidates() -> List[Dict[str, Any]]:
        try:
            embedder = get_async_embedder()
            query_vector = embedder.embed_query(patient_context[:1000])
            patient_entities = extract_clinical_entities(patient_context)

            conn = psycopg2.connect(DATABASE_URL, connect_timeout=15)
            cur = conn.cursor()

            # Retrieve top candidates from PGVector excluding the current trial
            cur.execute("""
                SELECT doc_id, COALESCE(title, doc_id), content, 1 - (embedding <=> %s::vector) AS vector_sim
                FROM trial_embeddings
                WHERE doc_id != %s
                ORDER BY vector_sim DESC
                LIMIT 15;
            """, (query_vector, current_trial_id))

            candidates = cur.fetchall()
            cur.close()
            conn.close()

            scored_trials = []
            for doc_id, raw_title, content, vector_sim in candidates:
                trial_entities = extract_clinical_entities(content)
                
                v_score = max(0.0, float(vector_sim))
                bm_score = calculate_jaccard_similarity(patient_entities["biomarkers"], trial_entities["biomarkers"])
                st_score = calculate_jaccard_similarity(patient_entities["stages"], trial_entities["stages"])
                
                shared_bms = patient_entities["biomarkers"].intersection(trial_entities["biomarkers"])
                if shared_bms:
                    bm_score = max(bm_score, 0.85)

                composite_score = (v_score * 0.50) + (bm_score * 0.30) + (st_score * 0.20)
                
                cond_match = re.search(r"(?:Target Conditions?|Target Condition|Conditions?):?\s*([^\n]+)", content, re.IGNORECASE)
                condition_str = cond_match.group(1).strip() if cond_match else "Target Oncology Indication"

                shared_details = []
                if shared_bms:
                    shared_details.append(f"aligned biomarkers ({', '.join(sorted(list(shared_bms))).upper()})")
                shared_stages = patient_entities["stages"].intersection(trial_entities["stages"])
                if shared_stages:
                    shared_details.append(f"compatible staging ({', '.join(sorted(list(shared_stages))).title()})")
                
                if shared_details:
                    rationale = f"High dynamic fit: {' and '.join(shared_details)} targeting {clean_truncate_title(condition_str, 60)}."
                else:
                    rationale = f"High semantic vector alignment to patient primary clinical profile ({clean_truncate_title(condition_str, 60)})."

                scored_trials.append({
                    "trial_id": str(doc_id),
                    "trial_title": clean_truncate_title(raw_title, max_chars=130),
                    "similarity_match_score": f"{round(composite_score * 100, 1)}%",
                    "_raw_score": composite_score,
                    "match_rationale": rationale
                })

            scored_trials.sort(key=lambda x: x["_raw_score"], reverse=True)
            top_alternatives = scored_trials[:limit]

            for t in top_alternatives:
                t.pop("_raw_score", None)

            return top_alternatives
        except Exception as e:
            print(f"⚠️ Dynamic Alternative Similarity Error: {e}")
            return []

    return await run_in_worker_thread(_re_rank_candidates)