import re
from typing import Dict, Any, Optional, Tuple, Set

# Universal Absolute Safety Contraindications
KNOWN_DISQUALIFYING_CONDITIONS = [
    (r"\bactive\s+brain\s+metastases\b", "Active untreated brain metastases"),
    (r"\bactive\s+(?:hiv|hepatitis\s+[bc])\b", "Active uncontrolled systemic infection (HIV/Hep B/C)"),
    (r"\bpregnancy\b|\bpregnant\b|\blactating\b", "Pregnancy or active lactation"),
    (r"\bautoimmune\s+disease\b.*\bimmunosuppressive\b", "Autoimmune disease requiring active systemic immunosuppression"),
    (r"\bsevere\s+cardiac\s+(?:failure|impairment|dysfunction)\b", "Severe baseline cardiac dysfunction / NYHA Class III-IV"),
]

def extract_numeric_ecog(text: str) -> Optional[int]:
    """Extracts numeric ECOG status integer from clinical text."""
    match = re.search(r"\becog(?:[\s\w]*status|[\s\w]*ps)?[\s:]*([0-4])\b", text, re.IGNORECASE)
    if match:
        return int(match.group(1))
    return None

def extract_biomarkers(text: str) -> Set[str]:
    """Extracts explicit oncology genomic markers and mutation profiles."""
    markers = set()
    lower_text = text.lower()
    
    gene_list = ["egfr", "braf", "kras", "alk", "ros1", "ret", "her2", "pdl1", "pd-l1", "msi-h"]
    for gene in gene_list:
        if re.search(rf"\b{re.escape(gene)}\b", lower_text):
            markers.add(gene)
            
    if "v600e" in lower_text:
        markers.add("braf_v600e")
    if "exon 19" in lower_text:
        markers.add("egfr_exon19_del")
    if "exon 20" in lower_text:
        markers.add("egfr_exon20_ins")
    if "alk rearrangement" in lower_text or "alk positive" in lower_text:
        markers.add("alk_positive")
        
    return markers

def evaluate_fast_path_rules(patient_context: str, trial_context: str) -> Optional[Dict[str, Any]]:
    """
    Deterministic Safety Pre-Filter.
    Detects safety boundary violations to prevent unnecessary compute while leaving
    all clinical and eligibility reasoning to the LLM and ML agents.
    """
    p_lower = patient_context.lower()
    t_lower = trial_context.lower()
    
    # 1. Deterministic Performance Status Check (Strict Severe Baseline Impairment)
    p_ecog = extract_numeric_ecog(patient_context)
    if p_ecog is not None:
        if p_ecog >= 3:
            return {
                "fast_path_disqualified": True,
                "inclusion_passed": False,
                "exclusion_cleared": False,
                "inclusion_reasoning": f"Deterministic Safety Gate: Patient ECOG status ({p_ecog}) indicates severe physical impairment incompatible with trial participation.",
                "exclusion_reasoning": "Deterministic Safety Gate: Baseline ECOG >= 3 violates standard trial safety requirements.",
                "disqualification_type": "SEVERE_ECOG_DISABILITY"
            }

    # 2. Incompatible Driver Translocations / Safety Exclusions
    p_markers = extract_biomarkers(patient_context)
    
    if "alk_positive" in p_markers and ("alk rearrangement positive" in t_lower or "alk-positive" in t_lower or "alk positive" in t_lower) and "exclusion" in t_lower:
        return {
            "fast_path_disqualified": True,
            "inclusion_passed": False,
            "exclusion_cleared": False,
            "inclusion_reasoning": "Deterministic Safety Gate: Patient possesses active ALK gene rearrangement.",
            "exclusion_reasoning": "Deterministic Safety Gate: Active ALK positivity triggers explicit protocol exclusion criteria.",
            "disqualification_type": "CONTRAINDICATED_MUTATION"
        }

    # 3. Known Absolute Safety Contraindications
    for pattern, description in KNOWN_DISQUALIFYING_CONDITIONS:
        if re.search(pattern, p_lower) and re.search(pattern, t_lower) and "exclusion" in t_lower:
            return {
                "fast_path_disqualified": True,
                "inclusion_passed": False,
                "exclusion_cleared": False,
                "inclusion_reasoning": f"Deterministic Safety Gate: Documented {description}.",
                "exclusion_reasoning": f"Deterministic Safety Gate: Documented {description} triggers mandatory trial safety exclusion criteria.",
                "disqualification_type": "SAFETY_CONTRAINDICATION"
            }

    return None