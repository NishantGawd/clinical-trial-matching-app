/**
 * lib/api.ts
 *
 * Typed fetch client for the Clinical Trial Matching Engine FastAPI backend
 * (main.py). Every function maps 1:1 to a REST endpoint exposed there.
 *
 * - Base URL comes from NEXT_PUBLIC_API_BASE_URL (defaults to
 *   http://localhost:8000, matching `uvicorn.run(..., port=8000)` in main.py).
 * - Requests are aborted after a timeout and surfaced as ApiRequestError,
 *   since the multi-agent swarm path can legitimately take 10-70s (per the
 *   sample phase3 report), while listing/health calls should fail fast.
 * - ApiRequestError carries a short, user-safe `message` for on-screen
 *   display plus a `debugDetail` string (host/path/status included) that UI
 *   components may show behind a "Technical details" disclosure, but never
 *   render by default — end users should never see raw hostnames or ports.
 */

import type {
  BatchMatchRequest,
  BatchMatchResponse,
  HealthResponse,
  MatchRequest,
  MatchResponse,
  PatientDetail,
  PatientListResponse,
  TrialDetail,
  TrialListResponse,
} from "@/types/clinical";

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") || "http://localhost:8000";

/** Fast endpoints (health/list) get a short timeout. */
const DEFAULT_TIMEOUT_MS = 15_000;
/** /api/match can run the full LLM swarm (observed 20-70s in phase3 report). */
const MATCH_TIMEOUT_MS = 120_000;

export class ApiRequestError extends Error {
  status?: number;
  /** Raw backend `detail` string, if the server returned one. */
  detail?: string;
  /** Verbose, developer-facing description (includes host/path/status). Never shown to end users by default. */
  debugDetail: string;

  constructor(message: string, debugDetail: string, status?: number, detail?: string) {
    super(message);
    this.name = "ApiRequestError";
    this.status = status;
    this.detail = detail;
    this.debugDetail = debugDetail;
  }
}

interface RequestOptions extends RequestInit {
  timeoutMs?: number;
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { timeoutMs = DEFAULT_TIMEOUT_MS, ...init } = options;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      signal: controller.signal,
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
        ...(init.headers || {}),
      },
      cache: "no-store",
    });
  } catch (err) {
    clearTimeout(timer);
    if (err instanceof DOMException && err.name === "AbortError") {
      throw new ApiRequestError(
        "That request is taking longer than expected. The matching service may be busy — please try again shortly.",
        `Timed out after ${Math.round(timeoutMs / 1000)}s calling ${API_BASE_URL}${path}`,
      );
    }
    throw new ApiRequestError(
      "We couldn't reach the matching engine service. Please check your connection and try again.",
      `Network error calling ${API_BASE_URL}${path}: ${err instanceof Error ? err.message : String(err)}`,
    );
  }
  clearTimeout(timer);

  const isJson = response.headers.get("content-type")?.includes("application/json");
  const body = isJson ? await response.json().catch(() => null) : null;

  if (!response.ok) {
    const detail =
      (body && typeof body === "object" && "detail" in body && String((body as { detail: unknown }).detail)) ||
      response.statusText;
    const friendly =
      response.status === 404
        ? "That record could not be found."
        : response.status >= 500
          ? "The matching engine service ran into a problem processing that request."
          : "That request could not be completed.";
    throw new ApiRequestError(
      friendly,
      `${response.status} ${response.statusText} on ${path}: ${detail}`,
      response.status,
      detail,
    );
  }

  return body as T;
}

// ---------------------------------------------------------------------------
// System
// ---------------------------------------------------------------------------

export function getHealth(): Promise<HealthResponse> {
  return request<HealthResponse>("/api/health");
}

// ---------------------------------------------------------------------------
// Clinical Data
// ---------------------------------------------------------------------------

export function listPatients(params: { limit?: number; search?: string } = {}): Promise<PatientListResponse> {
  const qs = new URLSearchParams();
  qs.set("limit", String(params.limit ?? 50));
  if (params.search) qs.set("search", params.search);
  return request<PatientListResponse>(`/api/patients?${qs.toString()}`);
}

export function getPatientDetail(patientId: string): Promise<PatientDetail> {
  return request<PatientDetail>(`/api/patients/${encodeURIComponent(patientId)}`);
}

export function listTrials(params: { limit?: number; search?: string } = {}): Promise<TrialListResponse> {
  const qs = new URLSearchParams();
  qs.set("limit", String(params.limit ?? 50));
  if (params.search) qs.set("search", params.search);
  return request<TrialListResponse>(`/api/trials?${qs.toString()}`);
}

export function getTrialDetail(trialId: string): Promise<TrialDetail> {
  return request<TrialDetail>(`/api/trials/${encodeURIComponent(trialId)}`);
}

// ---------------------------------------------------------------------------
// Engine Inference
// ---------------------------------------------------------------------------

export function runMatch(payload: MatchRequest): Promise<MatchResponse> {
  return request<MatchResponse>("/api/match", {
    method: "POST",
    body: JSON.stringify(payload),
    timeoutMs: MATCH_TIMEOUT_MS,
  });
}

export function runBatchMatch(payload: BatchMatchRequest): Promise<BatchMatchResponse> {
  return request<BatchMatchResponse>("/api/match/batch", {
    method: "POST",
    body: JSON.stringify(payload),
    timeoutMs: MATCH_TIMEOUT_MS,
  });
}
