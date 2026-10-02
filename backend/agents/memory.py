import psycopg2
import json
import re
from typing import List, Dict, Any, Optional
from config import DATABASE_URL
from langchain_huggingface import HuggingFaceEmbeddings

_memory_embeddings = None

def get_memory_embedder():
    """Singleton getter for memory vector embeddings."""
    global _memory_embeddings
    if _memory_embeddings is None:
        _memory_embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    return _memory_embeddings

def init_prompt_memory_table():
    """
    Initializes the prompt_memory table in PostgreSQL with 
    IVFFlat index support for sub-millisecond few-shot semantic retrieval.
    """
    try:
        conn = psycopg2.connect(DATABASE_URL, connect_timeout=15)
        cur = conn.cursor()
        
        # Ensure pgvector extension exists
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        
        # Create prompt_memory table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS prompt_memory (
                id SERIAL PRIMARY KEY,
                case_key VARCHAR(120) UNIQUE NOT NULL,
                patient_id VARCHAR(64) NOT NULL,
                trial_id VARCHAR(64) NOT NULL,
                condition_category VARCHAR(120),
                clinical_summary TEXT NOT NULL,
                inclusion_decision VARCHAR(10) NOT NULL,
                inclusion_reasoning TEXT NOT NULL,
                exclusion_decision VARCHAR(10) NOT NULL,
                exclusion_reasoning TEXT NOT NULL,
                overall_match BOOLEAN NOT NULL,
                auditor_verified BOOLEAN DEFAULT TRUE,
                embedding VECTOR(384),
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # Create Cosine Similarity Index for rapid vector retrieval
        cur.execute("""
            CREATE INDEX IF NOT EXISTS prompt_memory_embedding_idx 
            ON prompt_memory USING ivfflat (embedding vector_cosine_ops)
            WITH (lists = 50);
        """)
        
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"⚠️ Prompt Memory Table Initialization Warning: {e}")

# Initialize schema on module import
init_prompt_memory_table()

def store_verified_match_memory(
    patient_id: str,
    trial_id: str,
    patient_context: str,
    trial_context: str,
    inclusion_passed: bool,
    inclusion_reasoning: str,
    exclusion_cleared: bool,
    exclusion_reasoning: str,
    overall_match: bool
) -> bool:
    """
    Stores an auditor-verified decision into PGVector for continual learning.
    """
    try:
        case_key = f"{patient_id.strip()}_{trial_id.strip()}"
        
        # Extract condition/indication keyword dynamically from text
        cond_match = re.search(
            r'(?:DIAGNOSIS|Target Condition|Condition|CHIEF COMPLAINT)[\s:]*([^\n]+)',
            patient_context + "\n" + trial_context,
            re.IGNORECASE
        )
        condition_cat = cond_match.group(1).strip()[:100] if cond_match else "General Medicine"
        
        # Extract succinct clinical summary for embedding
        clinical_summary = f"""
PATIENT CASE: {patient_id} | TRIAL: {trial_id}
CONDITION: {condition_cat}
PATIENT PROFILE: {patient_context[:300].strip()}
TRIAL CRITERIA: {trial_context[:300].strip()}
""".strip()

        embedder = get_memory_embedder()
        vector = embedder.embed_query(clinical_summary)
        
        inc_decision = "YES" if inclusion_passed else "NO"
        exc_decision = "CLEARED" if exclusion_cleared else "EXCLUDED"
        
        conn = psycopg2.connect(DATABASE_URL, connect_timeout=15)
        cur = conn.cursor()
        
        cur.execute("""
            INSERT INTO prompt_memory (
                case_key, patient_id, trial_id, condition_category, 
                clinical_summary, inclusion_decision, inclusion_reasoning, 
                exclusion_decision, exclusion_reasoning, overall_match, 
                auditor_verified, embedding
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (case_key) DO UPDATE SET
                condition_category = EXCLUDED.condition_category,
                clinical_summary = EXCLUDED.clinical_summary,
                inclusion_decision = EXCLUDED.inclusion_decision,
                inclusion_reasoning = EXCLUDED.inclusion_reasoning,
                exclusion_decision = EXCLUDED.exclusion_decision,
                exclusion_reasoning = EXCLUDED.exclusion_reasoning,
                overall_match = EXCLUDED.overall_match,
                auditor_verified = EXCLUDED.auditor_verified,
                embedding = EXCLUDED.embedding,
                created_at = CURRENT_TIMESTAMP;
        """, (
            case_key, patient_id, trial_id, condition_cat,
            clinical_summary, inc_decision, inclusion_reasoning,
            exc_decision, exclusion_reasoning, overall_match,
            True, vector
        ))
        
        conn.commit()
        cur.close()
        conn.close()
        print(f"  🧠 [Prompt Memory] Stored verified clinical case memory: {case_key}")
        return True
    except Exception as e:
        print(f"⚠️ Prompt Memory Storage Warning: {e}")
        return False

def retrieve_similar_few_shot_memories(
    patient_context: str,
    current_patient_id: str,
    limit: int = 2
) -> List[Dict[str, Any]]:
    """
    Retrieves top-K most similar historical matching cases from PGVector
    to inject as dynamic Few-Shot exemplars into Agent reasoning prompts.
    """
    try:
        embedder = get_memory_embedder()
        query_vector = embedder.embed_query(patient_context[:1000])
        
        conn = psycopg2.connect(DATABASE_URL, connect_timeout=15)
        cur = conn.cursor()
        
        # Query PGVector excluding the current patient to prevent self-referencing
        cur.execute("""
            SELECT 
                patient_id, trial_id, condition_category, 
                inclusion_decision, inclusion_reasoning,
                exclusion_decision, exclusion_reasoning,
                overall_match,
                1 - (embedding <=> %s::vector) AS similarity
            FROM prompt_memory
            WHERE patient_id != %s AND auditor_verified = TRUE
            ORDER BY similarity DESC
            LIMIT %s;
        """, (query_vector, current_patient_id, limit))
        
        rows = cur.fetchall()
        cur.close()
        conn.close()
        
        memories = []
        for r in rows:
            memories.append({
                "patient_id": r[0],
                "trial_id": r[1],
                "condition": r[2],
                "inclusion_decision": r[3],
                "inclusion_reasoning": r[4],
                "exclusion_decision": r[5],
                "exclusion_reasoning": r[6],
                "overall_match": bool(r[7]),
                "similarity_score": round(float(r[8]), 4)
            })
            
        return memories
    except Exception as e:
        print(f"⚠️ Prompt Memory Retrieval Warning: {e}")
        return []

def format_few_shot_prompt_context(memories: List[Dict[str, Any]], target_agent: str = "all") -> str:
    """
    Formats retrieved historical cases into clean Few-Shot blocks for LLM Prompts.
    """
    if not memories:
        return ""
    
    formatted_blocks = ["\nHISTORICAL VERIFIED CLINICAL EXEMPLARS (Learn and follow this standard of reasoning):"]
    
    for i, mem in enumerate(memories, 1):
        block = f"\n[Exemplar {i} - Condition: {mem['condition']} | Similarity: {round(mem['similarity_score'] * 100, 1)}%]"
        if target_agent in ["inclusion", "all"]:
            block += f"\n- INCLUSION OUTCOME: RESULT: {mem['inclusion_decision']}"
            block += f"\n- INCLUSION REASONING: {mem['inclusion_reasoning']}"
        if target_agent in ["exclusion", "all"]:
            block += f"\n- EXCLUSION OUTCOME: RESULT: {mem['exclusion_decision']}"
            block += f"\n- EXCLUSION REASONING: {mem['exclusion_reasoning']}"
        formatted_blocks.append(block)
        
    return "\n".join(formatted_blocks) + "\n"