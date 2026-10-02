from typing import TypedDict, Optional, Dict, Any, List

class MatchingState(TypedDict, total=False):
    """
    Dynamic State representation passed through the clinical matching agent graph.
    Tracks raw context, LLM-extracted patient metrics, reflection loops,
    and ML attrition risk scores dynamically without hardcoded constants.
    """
    patient_id: str
    trial_id: str
    
    # Raw EHR and Clinical Trial Protocol Context
    patient_context: str
    trial_context: str
    
    # Dynamic LLM-Extracted Patient Feature Representations for ML Modeling
    patient_metrics: Optional[Dict[str, Any]]
    
    # Vector-Retrieved Dynamic Few-Shot Clinical Memories
    few_shot_memories: Optional[List[Dict[str, Any]]]
    
    # Independent Agent Evaluation Decisions & Free-Text Clinical Reasoning
    inclusion_passed: Optional[bool]
    inclusion_reasoning: Optional[str]
    
    exclusion_cleared: Optional[bool]
    exclusion_reasoning: Optional[str]
    
    # Reflexion / Critic Node State
    audit_passed: Optional[bool]
    auditor_feedback: Optional[str]
    audit_loop_count: int
    
    # Dynamically Calibrated Scoring (Computed via LLM Certainty & ML Gating)
    overall_match: Optional[bool]
    extraction_confidence: Optional[float]
    eligibility_score: Optional[float]
    confidence_score: Optional[float]
    
    # Final Structured Synthesis Payload
    summary_report: Optional[Dict[str, Any]]
    error: Optional[str]