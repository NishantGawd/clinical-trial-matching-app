import asyncio
import hashlib
import time
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Coroutine, List, Optional
import psycopg2
from psycopg2 import pool
from langchain_huggingface import HuggingFaceEmbeddings

from config import DATABASE_URL, MAX_ASYNC_WORKERS

# Dedicated ThreadPoolExecutor to prevent CPU/IO blocking on the main event loop
_IO_WORKER_POOL = ThreadPoolExecutor(max_workers=MAX_ASYNC_WORKERS, thread_name_prefix="AsyncAgentWorker")
_EMBEDDINGS_SINGLETON: Optional[HuggingFaceEmbeddings] = None

# Thread-safe connection pool for PostgreSQL to eliminate per-query TCP handshakes
_DB_CONNECTION_POOL: Optional[pool.ThreadedConnectionPool] = None

# In-memory Thread-Safe LRU Cache for Embeddings (stores up to 2048 vectors)
_EMBED_CACHE_LOCK = asyncio.Lock()
_EMBEDDING_LRU_CACHE: OrderedDict[str, List[float]] = OrderedDict()
MAX_EMBED_CACHE_SIZE = 2048


def get_db_pool() -> pool.ThreadedConnectionPool:
    """Singleton getter for threaded PostgreSQL connection pool."""
    global _DB_CONNECTION_POOL
    if _DB_CONNECTION_POOL is None:
        _DB_CONNECTION_POOL = pool.ThreadedConnectionPool(
            minconn=2,
            maxconn=max(8, MAX_ASYNC_WORKERS),
            dsn=DATABASE_URL,
            connect_timeout=15
        )
    return _DB_CONNECTION_POOL


def get_async_embedder() -> HuggingFaceEmbeddings:
    """Singleton getter for HuggingFace embeddings."""
    global _EMBEDDINGS_SINGLETON
    if _EMBEDDINGS_SINGLETON is None:
        _EMBEDDINGS_SINGLETON = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True}
        )
    return _EMBEDDINGS_SINGLETON


async def run_in_worker_thread(func: Callable, *args, **kwargs) -> Any:
    """Offloads blocking synchronous functions (DB, Disk IO, ML matrix math) to the worker thread pool."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(_IO_WORKER_POOL, lambda: func(*args, **kwargs))


def _compute_text_hash(text: str) -> str:
    """Computes a lightweight SHA-256 fingerprint for cache indexing."""
    return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()


async def async_embed_query(text: str) -> List[float]:
    """
    Generates embeddings asynchronously with in-memory LRU caching.
    Avoids redundant PyTorch CPU tensor evaluations for identical or repeated clinical passages.
    """
    cleaned_text = text.strip()
    text_key = _compute_text_hash(cleaned_text)

    # 1. Fast path: Memory Cache hit (0.00ms latency)
    if text_key in _EMBEDDING_LRU_CACHE:
        _EMBEDDING_LRU_CACHE.move_to_end(text_key)
        return _EMBEDDING_LRU_CACHE[text_key]

    # 2. Compute embedding asynchronously via worker thread
    embedder = get_async_embedder()
    vector = await run_in_worker_thread(embedder.embed_query, cleaned_text)

    # 3. Store into LRU cache with evictions
    _EMBEDDING_LRU_CACHE[text_key] = vector
    if len(_EMBEDDING_LRU_CACHE) > MAX_EMBED_CACHE_SIZE:
        _EMBEDDING_LRU_CACHE.popitem(last=False)

    return vector


async def async_execute_db_query(query_sql: str, params: tuple = (), fetch_mode: str = "all") -> Any:
    """
    Executes a PostgreSQL query asynchronously using the connection pool
    to avoid opening and closing raw TCP connections on every call.
    """
    def _db_worker():
        db_pool = get_db_pool()
        conn = db_pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute(query_sql, params)
                if fetch_mode == "all":
                    results = cur.fetchall()
                elif fetch_mode == "one":
                    results = cur.fetchone()
                else:
                    conn.commit()
                    results = None
                return results
        finally:
            db_pool.putconn(conn)

    return await run_in_worker_thread(_db_worker)


async def execute_parallel_tasks(*coroutines: Coroutine) -> List[Any]:
    """
    Executes multiple coroutines concurrently using asyncio.gather with timing metrics
    and non-blocking exception captures.
    """
    start_time = time.time()
    results = await asyncio.gather(*coroutines, return_exceptions=True)
    duration = time.time() - start_time

    for idx, res in enumerate(results):
        if isinstance(res, Exception):
            print(f"⚠️ [Async Engine] Task {idx} raised an exception ({duration:.2f}s): {res}")

    return list(results)