import time
import psycopg2
from psycopg2.extras import execute_batch
from pathlib import Path
from langchain_community.document_loaders import TextLoader, PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from config import DATABASE_URL, ROOT_DIR

print("⚡ Loading Local Embedding Model (all-MiniLM-L6-v2) into memory...")
embeddings_model = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

def setup_optimized_vector_schema(cursor):
    """Sets up tables and HNSW indexes for ultra-fast vector retrieval."""
    cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    
    # Drop tables if they exist to allow clean re-runs
    cursor.execute("DROP TABLE IF EXISTS patient_embeddings CASCADE;")
    cursor.execute("DROP TABLE IF EXISTS trial_embeddings CASCADE;")
    
    # Create Tables (384 dimensions for all-MiniLM-L6-v2)
    cursor.execute("""
        CREATE TABLE patient_embeddings (
            id SERIAL PRIMARY KEY,
            doc_id VARCHAR(50),
            content TEXT,
            embedding vector(384)
        );
        CREATE TABLE trial_embeddings (
            id SERIAL PRIMARY KEY,
            doc_id VARCHAR(50),
            content TEXT,
            embedding vector(384)
        );
    """)
    
    # Create HNSW Indexes for blazing fast retrieval
    cursor.execute("""
        CREATE INDEX ON patient_embeddings USING hnsw (embedding vector_cosine_ops);
        CREATE INDEX ON trial_embeddings USING hnsw (embedding vector_cosine_ops);
    """)
    print("✅ Optimized Schema and HNSW Indexes Created.")

def ingest_directory(dir_path: Path, table_name: str, cursor):
    """Batched embedding and insertion pipeline for speed."""
    # OPTIMIZATION: Increased chunk_size to 1000 and overlap to 150 to keep medical criteria intact
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000, 
        chunk_overlap=150,
        separators=["\n\n", "\n", ".", " "]
    )
    
    insert_query = f"INSERT INTO {table_name} (doc_id, content, embedding) VALUES (%s, %s, %s)"
    batch_data = []
    
    files = list(dir_path.glob("*.*"))
    if not files:
        print(f"⚠️ No files found in {dir_path}")
        return

    for file_path in files:
        if file_path.suffix not in [".txt", ".pdf"]:
            continue
            
        loader = PyPDFLoader(str(file_path)) if file_path.suffix == ".pdf" else TextLoader(str(file_path))
        docs = loader.load()
        chunks = text_splitter.split_documents(docs)
        doc_id = file_path.stem
        
        for chunk in chunks:
            # Generate vector embedding
            vector = embeddings_model.embed_query(chunk.page_content)
            batch_data.append((doc_id, chunk.page_content, vector))
    
    # Execute high-speed batch insert
    if batch_data:
        execute_batch(cursor, insert_query, batch_data, page_size=100)
        print(f"✅ Ingested {len(batch_data)} chunks into '{table_name}'")

def run_ingestion():
    start_time = time.time()
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    
    print("\n[1/3] Setting up Vector Database Schema...")
    setup_optimized_vector_schema(cur)
    
    print("\n[2/3] Processing and Embedding Patient EHRs...")
    patients_dir = ROOT_DIR / "backend" / "data" / "ehr_patients"
    ingest_directory(patients_dir, "patient_embeddings", cur)
    
    print("\n[3/3] Processing and Embedding Trial Protocols...")
    trials_dir = ROOT_DIR / "backend" / "data" / "trial_protocols"
    ingest_directory(trials_dir, "trial_embeddings", cur)
    
    conn.commit()
    cur.close()
    conn.close()
    
    elapsed = time.time() - start_time
    print(f"\n🎉 RE-INDEXING COMPLETE: Data Chunking & Vectorization finished in {elapsed:.2f} seconds!")

if __name__ == "__main__":
    run_ingestion()