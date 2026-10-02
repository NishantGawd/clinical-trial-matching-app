import json
from typing import Optional, Dict, Any
import psycopg2
from psycopg2.extras import RealDictCursor
from config import DATABASE_URL


def setup_cache_table():
    """Initializes the result cache table in PostgreSQL with reasoning and metadata fields."""
    try:
        conn = psycopg2.connect(DATABASE_URL, connect_timeout=15)
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS match_results_cache (
                id SERIAL PRIMARY KEY,
                patient_id VARCHAR(50) NOT NULL,
                trial_id VARCHAR(50) NOT NULL,
                overall_match BOOLEAN NOT NULL,
                confidence_score FLOAT NOT NULL,
                inclusion_reasoning TEXT,
                exclusion_reasoning TEXT,
                summary_report JSONB NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(patient_id, trial_id)
            );
            CREATE INDEX IF NOT EXISTS idx_match_cache_lookup 
                ON match_results_cache (patient_id, trial_id);
        """)
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"⚠️ Cache table setup warning: {e}")


def get_cached_result(patient_id: str, trial_id: str) -> Optional[Dict[str, Any]]:
    """Checks if a complete evaluation report already exists in the cache."""
    try:
        conn = psycopg2.connect(DATABASE_URL, connect_timeout=10)
        cur = conn.cursor()
        cur.execute("""
            SELECT overall_match, confidence_score, inclusion_reasoning, exclusion_reasoning, summary_report 
            FROM match_results_cache 
            WHERE patient_id = %s AND trial_id = %s;
        """, (patient_id, trial_id))
        row = cur.fetchone()
        cur.close()
        conn.close()
        
        if row:
            summary = row[4]
            if isinstance(summary, str):
                try:
                    summary = json.loads(summary)
                except Exception:
                    pass
                    
            return {
                "overall_match": bool(row[0]),
                "confidence_score": float(row[1]),
                "inclusion_reasoning": row[2] or "",
                "exclusion_reasoning": row[3] or "",
                "summary_report": summary
            }
        return None
    except Exception as e:
        print(f"⚠️ Cache read error: {e}")
        return None


def save_to_cache(
    patient_id: str,
    trial_id: str,
    overall_match: bool,
    confidence_score: float,
    inclusion_reasoning: str,
    exclusion_reasoning: str,
    summary_report: dict
) -> bool:
    """Saves a newly generated LLM match report along with full agent reasonings to the cache."""
    try:
        conn = psycopg2.connect(DATABASE_URL, connect_timeout=10)
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO match_results_cache 
                (patient_id, trial_id, overall_match, confidence_score, inclusion_reasoning, exclusion_reasoning, summary_report)
            VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb)
            ON CONFLICT (patient_id, trial_id) 
            DO UPDATE SET 
                overall_match = EXCLUDED.overall_match,
                confidence_score = EXCLUDED.confidence_score,
                inclusion_reasoning = EXCLUDED.inclusion_reasoning,
                exclusion_reasoning = EXCLUDED.exclusion_reasoning,
                summary_report = EXCLUDED.summary_report,
                created_at = CURRENT_TIMESTAMP;
        """, (
            patient_id, 
            trial_id, 
            bool(overall_match), 
            float(confidence_score), 
            str(inclusion_reasoning), 
            str(exclusion_reasoning), 
            json.dumps(summary_report)
        ))
        conn.commit()
        cur.close()
        conn.close()
        print(f"  💾 Full transparent report cached for {patient_id} vs {trial_id}")
        return True
    except Exception as e:
        print(f"⚠️ Cache write error: {e}")
        return False