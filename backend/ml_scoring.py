import pickle
from pathlib import Path
from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd
from config import ROOT_DIR

MODEL_ARTIFACTS_FILE = ROOT_DIR / "backend" / "models" / "attrition_ml_artifacts.pkl"

_artifacts = None


def load_ml_artifacts():
    global _artifacts
    if _artifacts is None:
        if not MODEL_ARTIFACTS_FILE.exists():
            raise FileNotFoundError("ML Model missing. Run 'python backend/train_ml_model.py' first.")
        with open(MODEL_ARTIFACTS_FILE, "rb") as f:
            _artifacts = pickle.load(f)
    return _artifacts


def get_ecog_description(val: float) -> str:
    score = int(round(val))
    if score == 0:
        return "Fully active, asymptomatic baseline (ECOG 0)"
    elif score == 1:
        return "Restricted in physically strenuous activity but ambulatory (ECOG 1)"
    elif score == 2:
        return "Ambulatory, capable of self-care, unable to work (ECOG 2)"
    elif score == 3:
        return "Capable of limited self-care, confined to bed/chair >50% waking hours (ECOG 3)"
    else:
        return f"Completely disabled, confined to bed/chair (ECOG {score})"


FEATURE_DESCRIPTIONS = {
    "distance_miles": lambda val: f"Geographic travel distance ({val:.1f} miles from trial site)",
    "ecog_score": get_ecog_description,
    "toxicity_burden": lambda val: f"Cumulative physiological toxicity burden (Index {val:.1f})",
    "prior_treatments": lambda val: f"Extensive prior therapy lines ({int(val)} prior regimens)",
    "has_caregiver": lambda val: "Absence of dedicated home caregiver / living alone" if val == 0 else "Confirmed home caregiver and social support structure",
    "age": lambda val: f"Patient chronological age ({int(val)} years old)"
}


def generate_actionable_interventions(
    eval_metrics: Dict[str, Any], 
    is_eligible: bool = True
) -> List[Dict[str, str]]:
    """
    Generates tailored clinical, logistical, and social navigation interventions.
    If the candidate is ineligible for the target protocol, recommendations adapt
    to general pre-trial navigation to prepare them for alternative trials.
    """
    interventions = []
    has_caregiver = eval_metrics.get("has_caregiver", True)
    distance = float(eval_metrics.get("distance_miles", 0.0))
    toxicity = float(eval_metrics.get("toxicity_burden", 0.0))
    ecog = int(eval_metrics.get("ecog_score", 0))
    priors = int(eval_metrics.get("prior_treatments", 0))

    # 1. Caregiver & Social Navigation Support
    if not has_caregiver:
        detail = (
            "Assign a dedicated clinical trial nurse navigator and coordinate home health aide visits."
            if is_eligible else
            "Connect patient with oncology social work to evaluate community caregiver support for future trial matching."
        )
        interventions.append({
            "intervention_type": "Caregiver Support",
            "description": "Mitigate social isolation and unmonitored home compliance risks.",
            "implementation_details": detail
        })

    # 2. Transportation Assistance & Geographic Burden
    if distance >= 30.0:
        detail = (
            "Provide prepaid rideshare/shuttle coordination and hotel stipends for protocol visit days."
            if is_eligible else
            "Flag local community trial sites or decentralized trial options within a 15-mile radius."
        )
        interventions.append({
            "intervention_type": "Transportation Assistance",
            "description": f"Overcome substantial commute barrier ({distance:.1f} miles to center).",
            "implementation_details": detail
        })

    # 3. Toxicity Burden & Symptom Monitoring
    if toxicity >= 4.0:
        detail = (
            "Enroll in remote electronic patient-reported outcome (ePRO) tracking with weekly nurse triage calls."
            if is_eligible else
            "Initiate active supportive care optimization to reduce baseline toxicity burden prior to enrolling in alternative studies."
        )
        interventions.append({
            "intervention_type": "Toxicity Monitoring",
            "description": f"Proactively manage elevated baseline symptom burden (Score: {toxicity:.1f}).",
            "implementation_details": detail
        })

    # 4. Functional Mobility & Physical Rehabilitation
    if ecog >= 2:
        interventions.append({
            "intervention_type": "Functional Rehabilitation",
            "description": f"Support physical performance and functional stamina (Baseline ECOG: {ecog}).",
            "implementation_details": "Refer to oncology physical therapy for functional pre-habilitation and energy-conservation strategies."
        })

    # 5. Treatment Fatigue & Longitudinal Engagement
    if priors >= 3:
        interventions.append({
            "intervention_type": "Treatment Fatigue Support",
            "description": f"Prevent burnout in heavily pre-treated patient ({priors} prior regimens).",
            "implementation_details": "Incorporate supportive psycho-oncology check-ins to support longitudinal compliance."
        })

    return interventions


def evaluate_dynamic_gating(
    inclusion_passed: bool,
    exclusion_cleared: bool,
    extraction_confidence: float = 0.90,
    ecog_score: float = 1.0,
    toxicity_burden: float = 2.0
) -> Dict[str, Any]:
    """
    Evaluates dynamic gating and computes a continuous feasibility score (0.00 to 1.00).
    Anchors the starting score to empirical extraction confidence, deducting exact soft penalties.
    """
    hard_gate_passed = bool(inclusion_passed and exclusion_cleared)
    
    penalties = {}
    if not hard_gate_passed:
        eligibility_score = 0.00
        status_label = "DISQUALIFIED"
        penalties["hard_gate_penalty"] = 1.0
    else:
        # Dynamically anchored to the empirical clarity score of the record
        dynamic_conf = max(0.70, min(0.99, float(extraction_confidence)))
        base_score = dynamic_conf
        
        # Soft physiological deductions
        if ecog_score >= 2:
            ecog_pen = 0.10
            base_score -= ecog_pen
            penalties["ecog_penalty"] = -ecog_pen
        else:
            penalties["ecog_penalty"] = 0.0
            
        if toxicity_burden > 5.0:
            tox_pen = 0.08
            base_score -= tox_pen
            penalties["toxicity_penalty"] = -tox_pen
        else:
            penalties["toxicity_penalty"] = 0.0
            
        eligibility_score = round(max(0.50, min(0.99, base_score)), 2)
        status_label = "ELIGIBLE"
        
    return {
        "hard_gate_passed": hard_gate_passed,
        "eligibility_score": eligibility_score,
        "status_label": status_label,
        "extraction_confidence": round(float(extraction_confidence), 2),
        "penalties": penalties
    }


def predict_patient_attrition(
    age: float, 
    distance_miles: float, 
    prior_treatments: float, 
    ecog_score: float, 
    toxicity_burden: float, 
    has_caregiver: float,
    is_eligible: bool = True
) -> Dict[str, Any]:
    """
    Computes calibrated soft-voting probability across LightGBM, XGBoost, and Random Forest.
    Calculates SHAP explainability and targeted interventions across ALL patients, providing
    baseline frailty profiling regardless of trial inclusion/exclusion status.
    """
    artifacts = load_ml_artifacts()
    imputer = artifacts["imputer"]
    feature_names = artifacts["feature_names"]
    
    input_df = pd.DataFrame(
        [[age, distance_miles, prior_treatments, ecog_score, toxicity_burden, has_caregiver]], 
        columns=feature_names
    )
    input_imputed = imputer.transform(input_df)
    
    # 1. Calibrated Soft-Voting Inference (Tree-Ensemble)
    prob_lgb = float(artifacts["lgb_model"].predict_proba(input_imputed)[0][1])
    prob_xgb = float(artifacts["xgb_model"].predict_proba(input_imputed)[0][1])
    prob_rf  = float(artifacts["rf_model"].predict_proba(input_imputed)[0][1])
    
    calibrated_dropout_prob = (prob_lgb * 0.40) + (prob_xgb * 0.40) + (prob_rf * 0.20)
    
    # 2. Local Feature Interpretability via TreeExplainer
    shap_values = artifacts["explainer"].shap_values(input_imputed)
    patient_shap = shap_values[1][0] if isinstance(shap_values, list) else shap_values[0]
    
    feature_impacts = list(zip(feature_names, patient_shap, input_imputed[0]))
    feature_impacts.sort(key=lambda x: abs(x[1]), reverse=True)
    
    top_risk_factors, top_retention_factors = [], []
    for feat, impact, val in feature_impacts:
        desc_func = FEATURE_DESCRIPTIONS.get(feat, lambda v: f"{feat}: {v}")
        desc = desc_func(val)
        
        if impact > 0.08:
            top_risk_factors.append(desc)
        elif impact < -0.08:
            top_retention_factors.append(desc)

    # 3. Severity Categorization
    if calibrated_dropout_prob < 0.35:
        risk_level = "LOW"
    elif calibrated_dropout_prob < 0.65:
        risk_level = "MEDIUM"
    else:
        risk_level = "HIGH"
        
    eval_metrics = {
        "age": int(round(input_imputed[0][0])),
        "distance_miles": round(float(input_imputed[0][1]), 1),
        "prior_treatments": int(round(input_imputed[0][2])),
        "ecog_score": int(round(input_imputed[0][3])),
        "toxicity_burden": round(float(input_imputed[0][4]), 1),
        "has_caregiver": bool(input_imputed[0][5])
    }
    
    # 4. Generate Targeted Clinical/Logistical Interventions
    interventions = generate_actionable_interventions(eval_metrics, is_eligible=is_eligible)
    
    # 5. Domain Status Labeling
    status_label = "EVALUATED - TRIAL ACTIVE" if is_eligible else "EVALUATED - BASELINE FRAILTY PROFILE"
    status_message = (
        "Active protocol retention tracking engaged." 
        if is_eligible else 
        "Baseline frailty and attrition profile preserved to guide clinical navigation for alternative trials."
    )
        
    return {
        "status": status_label,
        "attrition_risk_level": risk_level,
        "dropout_probability_percent": f"{round(calibrated_dropout_prob * 100, 1)}%",
        "raw_dropout_probability": round(calibrated_dropout_prob, 4),
        "eval_metrics_used": eval_metrics,
        "primary_risk_drivers": top_risk_factors if top_risk_factors else ["No acute attrition risk factors identified."],
        "primary_retention_drivers": top_retention_factors if top_retention_factors else ["Standard clinical baseline stability."],
        "actionable_interventions": interventions,
        "message": status_message
    }