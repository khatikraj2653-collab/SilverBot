"""
Shared caching layer for SilverBot's tool functions.
Caches fetched factor data (not LLM scores) per unique call signature,
with a configurable TTL, persisted to SQLite so the cache survives
app restarts (unlike an in-memory dict, which is wiped on every reboot).
"""

import sqlite3
import os
import time
import hashlib
import functools


def _get_cache_db_path():
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'factor_cache.db')


def _init_cache_table():
    conn = sqlite3.connect(_get_cache_db_path())
    conn.execute("""
        CREATE TABLE IF NOT EXISTS factor_cache (
            cache_key TEXT PRIMARY KEY,
            value TEXT,
            cached_at REAL
        )
    """)
    conn.commit()
    conn.close()


_init_cache_table()


def cached_tool(ttl_seconds):
    """
    Decorator for caching a tool function's result for ttl_seconds, backed
    by SQLite so the cache persists across app restarts. Place this BELOW
    @tool (i.e. closer to the function) so it wraps the raw function before
    LangChain's @tool wraps it.

    Each call opens and closes its own SQLite connection (not shared across
    threads), so this is safe to use inside threaded/async contexts.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            key_raw = f"{func.__name__}:{args}:{sorted(kwargs.items())}"
            cache_key = hashlib.md5(key_raw.encode()).hexdigest()

            conn = sqlite3.connect(_get_cache_db_path())
            cursor = conn.execute(
                "SELECT value, cached_at FROM factor_cache WHERE cache_key = ?",
                (cache_key,)
            )
            row = cursor.fetchone()
            now = time.time()

            if row and (now - row[1]) < ttl_seconds:
                conn.close()
                return row[0]

            result = func(*args, **kwargs)

            conn.execute(
                "INSERT OR REPLACE INTO factor_cache (cache_key, value, cached_at) VALUES (?, ?, ?)",
                (cache_key, result, now)
            )
            conn.commit()
            conn.close()
            return result

        return wrapper
    return decorator


TTL_GOLD_SILVER = 7200     # 2 hr
TTL_RISK_SENTIMENT = 900   # 15 min
TTL_USD_INDEX = 86400      # 24 hr
TTL_RATE_ENV = 3600        # 1 hr
TTL_WEEKLY = 604800        # 7 days
TTL_GEOPOLITICAL = 7200    # 2 hr
