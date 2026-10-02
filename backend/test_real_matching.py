import os
import time
import psycopg2
from pathlib import Path
from langchain_community.embeddings import HuggingFaceEmbeddings
from config import DATABASE_URL, ROOT_DIR

# Define Output Directory & File
OUTPUT_DIR = ROOT_DIR / "backend" / "output"
os.makedirs(OUTPUT_DIR, exist_ok=True)
OUTPUT_FILE = OUTPUT_DIR / "real_data_match_results.txt"

print("⚡ Loading Embedding Model for deep vector retrieval...")
embeddings_model = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

def write_to_log(text: str, file_handle):
    """Prints to console and writes full untruncated text to file."""
    file_handle.write(text + "\n")

def evaluate_real_patient_match(patient_id: str, search_intent: str, file_handle):
    header = f"\n{'='*70}\n  DEEP MATCH EVALUATION: {patient_id}\n  Intent: '{search_intent}'\n{'='*70}"
    print(header)
    write_to_log(header, file_handle)
    
    # 1. Fetch Patient Document Content
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    
    cur.execute("SELECT content FROM patient_embeddings WHERE doc_id = %s LIMIT 1;", (patient_id,))
    patient_row = cur.fetchone()
    if not patient_row:
        msg = f"❌ Patient {patient_id} not found in vector database."
        print(msg)
        write_to_log(msg, file_handle)
        conn.close()
        return
        
    patient_text = patient_row[0]
    
    patient_info = f"\n📄 FULL PATIENT EHR RECORD:\n{patient_text}\n"
    print(patient_info[:300] + "...\n[Full EHR written to log file]")
    write_to_log(patient_info, file_handle)
    
    # 2. Generate Vector Embedding for Patient Search Query
    query_vector = embeddings_model.embed_query(f"{patient_text[:400]} {search_intent}")
    
    # 3. Retrieve Top Matching Real Clinical Trials using Cosine Distance
    sql_query = """
        SELECT doc_id, content, 1 - (embedding <=> %s::vector) AS similarity_score
        FROM trial_embeddings
        ORDER BY embedding <=> %s::vector
        LIMIT 3;
    """
    start_time = time.time()
    cur.execute(sql_query, (query_vector, query_vector))
    trial_matches = cur.fetchall()
    retrieval_time = time.time() - start_time
    
    time_msg = f"⚡ Retrieval Execution Time: {retrieval_time:.4f} seconds\n{'-'*70}"
    print(time_msg)
    write_to_log(time_msg, file_handle)
    
    for idx, (trial_id, trial_content, score) in enumerate(trial_matches, 1):
        match_summary = f"\n🏆 Rank #{idx} Match: Trial {trial_id} (Cosine Similarity: {score:.4f})\n"
        match_full_details = f"{match_summary}--- FULL TRIAL CRITERIA EXCERPT ---\n{trial_content}\n{'-'*50}"
        
        # Terminal gets a clean summary
        print(f"🏆 Rank #{idx} Match: Trial {trial_id} (Cosine Similarity: {score:.4f})")
        print(f"   Snippet: {trial_content[:150]}...\n")
        
        # Log file gets the ENTIRE untruncated content
        write_to_log(match_full_details, file_handle)
        
    cur.close()
    conn.close()

if __name__ == "__main__":
    banner = f"{'='*70}\n   PHASE 2 DEEP TEST: REAL DATA VECTOR MATCHING (FULL OUTPUT)\n{'='*70}"
    print(banner)
    
    with open(OUTPUT_FILE, "w", encoding="utf-8") as file_handle:
        write_to_log(banner, file_handle)
        
        # Test 1: Real Melanoma Patient
        evaluate_real_patient_match(
            patient_id="PAT_REAL_01", 
            search_intent="Stage III Melanoma BRAF V600E positive adjuvant trial",
            file_handle=file_handle
        )
        
        # Test 2: Real Lung Cancer Patient
        evaluate_real_patient_match(
            patient_id="PAT_REAL_02", 
            search_intent="Lung Cancer EGFR positive excluding active brain metastases",
            file_handle=file_handle
        )

    print(f"\n🎉 FULL DETAILED OUTPUT SAVED TO:\n   👉 {OUTPUT_FILE}")