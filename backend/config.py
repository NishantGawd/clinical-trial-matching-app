import os
import multiprocessing
from pathlib import Path
from dotenv import load_dotenv
from typing import Dict, Tuple, Any

# Resolve both root and backend directory locations for .env
ROOT_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = Path(__file__).resolve().parent

load_dotenv(ROOT_DIR / ".env")
load_dotenv(BACKEND_DIR / ".env")
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
RAW_GROQ_KEY = os.getenv("GROQ_API_KEY", "").strip()

# Explicitly ensure the API key is mirrored to the OS process environment
if RAW_GROQ_KEY:
    os.environ["GROQ_API_KEY"] = RAW_GROQ_KEY

from langchain_groq import ChatGroq

# Primary & High-Speed Production Models on Groq
MODEL_REASONING = os.getenv("MODEL_REASONING", "openai/gpt-oss-120b")
MODEL_STRUCTURED = os.getenv("MODEL_STRUCTURED", "openai/gpt-oss-120b")
MODEL_MEDICAL = os.getenv("MODEL_MEDICAL", "openai/gpt-oss-120b")

MODEL_FALLBACK_1 = os.getenv("MODEL_FALLBACK_1", "qwen/qwen3.6-27b")
MODEL_FALLBACK_2 = os.getenv("MODEL_FALLBACK_2", "openai/gpt-oss-20b")

# Concurrency & Worker Tuning
TOTAL_CPU_CORES = max(1, multiprocessing.cpu_count())
MAX_ASYNC_WORKERS = max(4, min(16, TOTAL_CPU_CORES * 2))
BATCH_CONCURRENCY_LIMIT = int(os.getenv("BATCH_CONCURRENCY_LIMIT", "8"))

# In-memory Singleton Cache for Persistent HTTP/2 Session Reuse
_LLM_CLIENT_CACHE: Dict[Tuple[str, float, bool, int], Any] = {}

def get_llm(
    model_name: str = MODEL_REASONING, 
    temperature: float = 0.05, 
    structured_json: bool = False,
    max_tokens: int = 1024
):
    """
    Returns a pooled, persistent LangChain ChatGroq instance with HTTP/2 keep-alive.
    Reuses existing connections across agent nodes to eliminate handshake latency.
    """
    api_key_val = os.environ.get("GROQ_API_KEY") or RAW_GROQ_KEY
    cache_key = (model_name, temperature, structured_json, max_tokens)

    if cache_key in _LLM_CLIENT_CACHE:
        return _LLM_CLIENT_CACHE[cache_key]

    model_kwargs = {"response_format": {"type": "json_object"}} if structured_json else {}

    primary_llm = ChatGroq(
        model=model_name,
        api_key=api_key_val,  # type: ignore
        temperature=temperature,
        max_tokens=max_tokens,
        model_kwargs=model_kwargs,
        max_retries=2,
        timeout=25.0
    )

    fallback_1 = ChatGroq(
        model=MODEL_FALLBACK_1,
        api_key=api_key_val,  # type: ignore
        temperature=temperature,
        max_tokens=max_tokens,
        model_kwargs=model_kwargs,
        max_retries=2,
        timeout=25.0
    )

    llm_pipeline = primary_llm.with_fallbacks([fallback_1])
    _LLM_CLIENT_CACHE[cache_key] = llm_pipeline
    return llm_pipeline