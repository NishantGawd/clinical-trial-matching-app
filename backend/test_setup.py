import time
import psycopg2
from config import (
    DATABASE_URL, 
    get_llm, 
    MODEL_REASONING, 
    MODEL_STRUCTURED, 
    MODEL_MEDICAL
)

def test_neon_connection():
    print("\n[1/4] Testing Neon Postgres Database Connection...")
    start_time = time.time()
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        conn.commit()
        cur.execute("SELECT version();")
        db_version = cur.fetchone()[0] #type: ignore
        elapsed = time.time() - start_time
        print(f"✅ Database Connected in {elapsed:.2f}s!\n    Postgres: {db_version[:35]}...")
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Database Connection Failed: {e}")
        return False

def benchmark_model_speed(role_name: str, model_id: str, test_prompt: str):
    print(f"\n⚡ Benchmarking {role_name} ({model_id})...")
    llm_chain = get_llm(model_id)
    
    # Run 1: Memory Load / Warmup
    warmup_start = time.time()
    _ = llm_chain.invoke(test_prompt)
    warmup_time = time.time() - warmup_start
    
    # Run 2: Optimized In-Memory Execution Speed Test
    exec_start = time.time()
    response = llm_chain.invoke(test_prompt)
    exec_time = time.time() - exec_start
    
    response_text = str(response).strip()
    approx_tokens = len(response_text.split())
    tokens_per_sec = approx_tokens / exec_time if exec_time > 0 else 0
    
    print(f"✅ Response Received in {exec_time:.2f} seconds! (Warmup: {warmup_time:.2f}s)")
    print(f"   Throughput: ~{tokens_per_sec:.1f} words/sec")
    print(f"   Sample Output: {response_text[:100]}...\n")
    return True

if __name__ == "__main__":
    print("======================================================")
    print("   PHASE 1: MULTI-MODEL SPEED & LATENCY BENCHMARK     ")
    print("======================================================")
    
    db_ok = test_neon_connection()
    
    # Test Medical Domain Model Speed
    med_ok = benchmark_model_speed(
        "Medical Specialist", 
        MODEL_MEDICAL, 
        "Define 'Hypertension' in 1 short sentence."
    )
    
    # Test Reasoning Model Speed
    reason_ok = benchmark_model_speed(
        "Reasoning Engine", 
        MODEL_REASONING, 
        "Explain in 1 concise sentence why Metformin is checked for renal insufficiency."
    )
    
    # Test Structured Model Speed
    struct_ok = benchmark_model_speed(
        "Structured Formatter", 
        MODEL_STRUCTURED, 
        "Return a JSON object with key 'status' and value 'active'."
    )

    if db_ok and med_ok and reason_ok and struct_ok:
        print("\n🎉 SPEED TEST COMPLETE: Models are warmed up in memory and operating at peak speed!")
        print("Ready for Phase 2 whenever you are.")
    else:
        print("\n⚠️ Benchmark incomplete. Check Ollama process.")