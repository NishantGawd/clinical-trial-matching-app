import os
import uvicorn
from typing import List, Optional, Dict, Any, cast
from fastapi import FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import psycopg2
from psycopg2.extras import RealDictCursor

from config import DATABASE_URL
from agents.graph import build_clinical_matching_graph
from agents.cache import get_cached_result
from agents.state import MatchingState

app = FastAPI(
    title="Clinical Trial Matching Engine API",
    description="Enterprise Multi-Agent Clinical Matching, Dynamic Gating, and ML Attrition API",
    version="1.0.0"
)

# Enable CORS for Next.js / React frontend (local dev and production ports)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Compile LangGraph runtime singleton once during app initialization
MATCHING_GRAPH = build_clinical_matching_graph()


# =========================================================================
# REQUEST & RESPONSE SCHEMAS
# =========================================================================
class MatchRequest(BaseModel):
    patient_id: str = Field(..., examples=["PAT_REAL_01"], description="Unique Patient Identifier")
    trial_id: str = Field(..., examples=["NCT06536257"], description="Target Clinical Trial ID")
    force_refresh: bool = Field(default=False, description="Bypasses database cache to force re-evaluation")


class BatchMatchRequest(BaseModel):
    matches: List[MatchRequest] = Field(..., description="List of patient-trial pairs to evaluate")


# =========================================================================
# REST ENDPOINTS
# =========================================================================
@app.get("/api/health", tags=["System"])
async def health_check():
    """Health check endpoint to verify backend operational readiness."""
    return {
        "status": "HEALTHY",
        "service": "clinical-trial-matching-engine",
        "version": "1.0.0"
    }


@app.get("/api/patients", tags=["Clinical Data"])
async def get_patients(
    limit: int = Query(50, ge=1, le=200, description="Max patients to return"),
    search: Optional[str] = Query(None, description="Optional search term to filter by patient ID or preview")
):
    """
    Fetches candidate patient profiles from PostgreSQL for frontend selection menus and tables.
    Returns doc_id, snippet preview, and full text length.
    """
    try:
        conn = psycopg2.connect(DATABASE_URL, connect_timeout=10)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        if search:
            query = """
                SELECT 
                    doc_id AS patient_id, 
                    SUBSTRING(content FROM 1 FOR 350) AS preview,
                    LENGTH(content) AS content_length
                FROM patient_embeddings
                WHERE doc_id ILIKE %s OR content ILIKE %s
                ORDER BY doc_id ASC
                LIMIT %s;
            """
            search_param = f"%{search.strip()}%"
            cur.execute(query, (search_param, search_param, limit))
        else:
            query = """
                SELECT 
                    doc_id AS patient_id, 
                    SUBSTRING(content FROM 1 FOR 350) AS preview,
                    LENGTH(content) AS content_length
                FROM patient_embeddings
                ORDER BY doc_id ASC
                LIMIT %s;
            """
            cur.execute(query, (limit,))
            
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return {"count": len(rows), "patients": rows}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database query failed: {str(e)}"
        )


@app.get("/api/patients/{patient_id}", tags=["Clinical Data"])
async def get_patient_detail(patient_id: str):
    """Fetches the full un-truncated EHR text for a single patient."""
    try:
        conn = psycopg2.connect(DATABASE_URL, connect_timeout=10)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(
            "SELECT doc_id AS patient_id, content FROM patient_embeddings WHERE doc_id = %s LIMIT 1;", 
            (patient_id.strip(),)
        )
        row = cur.fetchone()
        cur.close()
        conn.close()
        
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail=f"Patient '{patient_id}' not found in database."
            )
            
        return row
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Database query failed: {str(e)}"
        )


@app.get("/api/trials", tags=["Clinical Data"])
async def get_trials(
    limit: int = Query(50, ge=1, le=200, description="Max trials to return"),
    search: Optional[str] = Query(None, description="Optional search term to filter by trial ID or criteria")
):
    """
    Fetches active protocol titles and IDs for trial selection menus and cards.
    """
    try:
        conn = psycopg2.connect(DATABASE_URL, connect_timeout=10)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        if search:
            query = """
                SELECT 
                    doc_id AS trial_id, 
                    SUBSTRING(content FROM 1 FOR 350) AS preview,
                    LENGTH(content) AS content_length
                FROM trial_embeddings
                WHERE doc_id ILIKE %s OR content ILIKE %s
                ORDER BY doc_id ASC
                LIMIT %s;
            """
            search_param = f"%{search.strip()}%"
            cur.execute(query, (search_param, search_param, limit))
        else:
            query = """
                SELECT 
                    doc_id AS trial_id, 
                    SUBSTRING(content FROM 1 FOR 350) AS preview,
                    LENGTH(content) AS content_length
                FROM trial_embeddings
                ORDER BY doc_id ASC
                LIMIT %s;
            """
            cur.execute(query, (limit,))
            
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return {"count": len(rows), "trials": rows}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Database query failed: {str(e)}"
        )


@app.get("/api/trials/{trial_id}", tags=["Clinical Data"])
async def get_trial_detail(trial_id: str):
    """Fetches the full un-truncated protocol criteria for a single trial."""
    try:
        conn = psycopg2.connect(DATABASE_URL, connect_timeout=10)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(
            "SELECT doc_id AS trial_id, content FROM trial_embeddings WHERE doc_id = %s LIMIT 1;", 
            (trial_id.strip(),)
        )
        row = cur.fetchone()
        cur.close()
        conn.close()
        
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail=f"Trial '{trial_id}' not found in database."
            )
            
        return row
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Database query failed: {str(e)}"
        )


@app.post("/api/match", tags=["Engine Inference"])
async def execute_match(req: MatchRequest):
    """
    Executes the multi-agent swarm matching pipeline for a patient-trial pair.
    Checks PostgreSQL cache first unless `force_refresh` is set to True.
    """
    patient_id = req.patient_id.strip()
    trial_id = req.trial_id.strip()

    # 1. Instant Cache Inspection
    if not req.force_refresh:
        cached = get_cached_result(patient_id, trial_id)
        if cached and cached.get("summary_report"):
            return {
                "source": "CACHE",
                "execution_mode": "SUB_MILLISECOND_CACHED",
                "data": cached["summary_report"]
            }

    # 2. Pipeline State Initialization
    initial_state = {
        "patient_id": patient_id,
        "trial_id": trial_id,
        "patient_context": "",
        "trial_context": "",
        "few_shot_memories": [],
        "inclusion_passed": None,
        "inclusion_reasoning": "",
        "exclusion_cleared": None,
        "exclusion_reasoning": "",
        "auditor_feedback": "",
        "audit_passed": None,
        "audit_loop_count": 0,
        "extraction_confidence": 0.0,
        "eligibility_score": 0.0,
        "confidence_score": 0.0,
        "overall_match": False,
        "summary_report": {},
        "error": None
    }

    # 3. Asynchronous Graph Swarm Execution
    try:
        final_state = await MATCHING_GRAPH.ainvoke(cast(MatchingState, initial_state))
        report = final_state.get("summary_report")
        if not report:
            raise ValueError("Pipeline completed without producing a valid summary report.")

        route_mode = "DETERMINISTIC_FAST_PATH" if final_state.get("error") == "FAST_PATH_EXIT" else "PARALLEL_MULTI_AGENT_SWARM"

        return {
            "source": "LIVE_EVALUATION",
            "execution_mode": route_mode,
            "data": report
        }
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Matching pipeline failed: {str(err)}"
        )


@app.post("/api/match/batch", tags=["Engine Inference"])
async def execute_batch_matches(batch_req: BatchMatchRequest):
    """
    Executes multiple patient-trial evaluations sequentially or via cache.
    Useful for batch screening a single patient against multiple trials.
    """
    results = []
    for item in batch_req.matches:
        try:
            res = await execute_match(item)
            results.append({
                "patient_id": item.patient_id,
                "trial_id": item.trial_id,
                "status": "SUCCESS",
                "result": res
            })
        except Exception as e:
            results.append({
                "patient_id": item.patient_id,
                "trial_id": item.trial_id,
                "status": "ERROR",
                "detail": str(e)
            })
            
    return {"total_evaluated": len(results), "results": results}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)