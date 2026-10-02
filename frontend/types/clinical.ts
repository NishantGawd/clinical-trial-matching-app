/**
 * types/clinical.ts
 *
 * Mirrors the backend Pydantic contracts 1:1:
 *   - agents/nodes.py  -> ExtractedPatientFeatures, ActionableIntervention,
 *                         MLAttritionRisk, AlternativeTrial, CalibrationMetrics,
 *                         FinalMatchSummary
 *   - main.py           -> MatchRequest, BatchMatchRequest, list/health responses
 *
 * Field names, casing, and optionality are kept identical to the Python side
 * so the JSON returned by FastAPI can be assigned to these types with zero
 * transformation.
 */

// ---------------------------------------------------------------------------
// System
// ---------------------------------------------------------------------------

export interface HealthResponse {
  status: "HEALTHY" | string;
  service: string;
  version?: string;
}

// ---------------------------------------------------------------------------
// Clinical Data — /api/patients, /api/trials
// ---------------------------------------------------------------------------

export interface Patient {
  patient_id: string;
  preview: string;
  content_length?: number;
}

export interface PatientListResponse {
  count: number;
  patients: Patient[];
}

export interface PatientDetail {
  patient_id: string;
  content: string;
}

export interface Trial {
  trial_id: string;
  preview: string;
  content_length?: number;
}

export interface TrialListResponse {
  count: number;
  trials: Trial[];
}

export interface TrialDetail {
  trial_id: string;
  content: string;
}

// ---------------------------------------------------------------------------
// Engine Inference — /api/match, /api/match/batch
// ---------------------------------------------------------------------------

export interface MatchRequest {
  patient_id: string;
  trial_id: string;
  force_refresh?: boolean;
}

export interface BatchMatchRequest {
  matches: MatchRequest[];
}

/** ExtractedPatientFeatures (agents/nodes.py) */
export interface ExtractedPatientFeatures {
  age: number;
  distance_miles: number;
  prior_treatments: number;
  ecog_score: number;
  toxicity_burden: number;
  has_caregiver: number;
}

/** ActionableIntervention (agents/nodes.py) */
export interface ActionableIntervention {
  intervention_type: string;
  description: string;
  implementation_details?: string | null;
}

/** Feature vector as echoed back inside ml_attrition_risk.eval_metrics_used */
export interface EvalMetricsUsed {
  age: number;
  distance_miles: number;
  prior_treatments: number;
  ecog_score: number;
  toxicity_burden: number;
  has_caregiver: boolean;
  [key: string]: number | boolean;
}

export type AttritionRiskLevel = "LOW" | "MEDIUM" | "HIGH" | string;

/** MLAttritionRisk (agents/nodes.py) */
export interface MLAttritionRisk {
  status: string;
  attrition_risk_level?: AttritionRiskLevel | null;
  dropout_probability_percent?: string | null;
  raw_dropout_probability?: number | null;
  primary_risk_drivers: string[];
  primary_retention_drivers: string[];
  eval_metrics_used: EvalMetricsUsed | Record<string, never>;
  actionable_interventions: ActionableIntervention[];
  message?: string | null;
}

/** AlternativeTrial (agents/nodes.py) */
export interface AlternativeTrial {
  trial_id: string;
  trial_title: string;
  /** Pre-formatted percent string, e.g. "66.2%" */
  similarity_match_score: string;
  match_rationale: string;
}

/** CalibrationMetrics (agents/nodes.py) */
export interface CalibrationMetrics {
  hard_gate_passed: boolean;
  metric_calibration_method: string;
  gating_penalties: Record<string, number>;
}

export type InclusionStatus = "PASSED" | "FAILED" | string;
export type ExclusionStatus = "CLEARED" | "DISQUALIFIED" | string;

/** FinalMatchSummary (agents/nodes.py) — the `data` payload of a /api/match response */
export interface FinalMatchSummary {
  patient_id: string;
  trial_id: string;
  overall_match: boolean;
  extraction_confidence: number;
  eligibility_score: number;
  confidence_score: number;
  calibration_breakdown?: CalibrationMetrics | null;
  inclusion_status: InclusionStatus;
  exclusion_status: ExclusionStatus;
  match_summary: string;
  ml_attrition_risk: MLAttritionRisk;
  alternative_trials: AlternativeTrial[];
}

export type MatchSource = "CACHE" | "LIVE_EVALUATION" | "LIVE_MULTI_AGENT_SWARM" | string;
export type ExecutionMode =
  | "SUB_MILLISECOND_CACHED"
  | "DETERMINISTIC_FAST_PATH"
  | "PARALLEL_MULTI_AGENT_SWARM"
  | "CALIBRATED_EVALUATION"
  | string;

/** Full response envelope from POST /api/match */
export interface MatchResponse {
  source: MatchSource;
  execution_mode: ExecutionMode;
  data: FinalMatchSummary;
}

export interface BatchMatchResultItem {
  patient_id: string;
  trial_id: string;
  status: "SUCCESS" | "ERROR";
  result?: MatchResponse;
  detail?: string;
}

export interface BatchMatchResponse {
  total_evaluated: number;
  results: BatchMatchResultItem[];
}

// ---------------------------------------------------------------------------
// UI-local helper types (not part of the backend contract)
// ---------------------------------------------------------------------------

/** Identifies which swarm node is currently active for the live visualizer. */
export type SwarmNodeId =
  | "retrieval"
  | "inclusion"
  | "exclusion"
  | "critic"
  | "synthesis";

export interface SwarmNodeState {
  id: SwarmNodeId;
  label: string;
  status: "idle" | "active" | "done" | "error";
}

export interface ApiError {
  detail: string;
  status?: number;
}
