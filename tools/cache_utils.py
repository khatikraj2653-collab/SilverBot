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


# Strings that indicate a failed fetch — we skip caching these so a transient
# rate limit or API hiccup doesn't poison the cache for hours.
_ERROR_MARKERS = (
    "Data unavailable",
    "Data temporarily unavailable",
    "Too Many Requests",
    "Rate limited",
    "Try after a while",
    "Cannot specify",
    "out-of-bounds",
    "all sources failed",
    "N/A for ",
    "no usable content",
    "None (Gold: $None",
)


def _looks_like_error(value: str) -> bool:
    """True if the string looks like a failed fetch / missing-data placeholder
    rather than a real signal. Used both for cache-skip and for the scoring
    guardrail so the LLM never scores an error string as bullish/bearish."""
    if not isinstance(value, str) or not value.strip():
        return True
    if any(m in value for m in _ERROR_MARKERS):
        return True
    na_count = value.count("N/A") + value.count("n/a")
    digit_count = sum(c.isdigit() for c in value)
    # Require OVERWHELMINGLY placeholders before flagging as error.
    if na_count >= 3 and digit_count < 2:
        return True
    return False


def cached_tool(ttl_seconds):
    """
    Decorator for caching a tool function's result for ttl_seconds, backed
    by SQLite so the cache persists across app restarts. Place this BELOW
    @tool (i.e. closer to the function) so it wraps the raw function before
    LangChain's @tool wraps it.

    Error responses are NOT cached — previously a transient rate-limit error
    could poison the cache and users kept seeing the same stale error.
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

            # Serve from cache ONLY if the cached value isn't an error string
            if row and (now - row[1]) < ttl_seconds and not _looks_like_error(row[0]):
                conn.close()
                return row[0]

            result = func(*args, **kwargs)

            if _looks_like_error(result):
                conn.execute("DELETE FROM factor_cache WHERE cache_key = ?", (cache_key,))
                conn.commit()
                conn.close()
                return result

            conn.execute(
                "INSERT OR REPLACE INTO factor_cache (cache_key, value, cached_at) VALUES (?, ?, ?)",
                (cache_key, result, now)
            )
            conn.commit()
            conn.close()
            return result

        return wrapper
    return decorator


def purge_error_cache():
    """Wipe any cached error rows left over from before error-skipping existed."""
    try:
        conn = sqlite3.connect(_get_cache_db_path())
        cursor = conn.execute("SELECT cache_key, value FROM factor_cache")
        bad = [row[0] for row in cursor.fetchall() if _looks_like_error(row[1])]
        for key in bad:
            conn.execute("DELETE FROM factor_cache WHERE cache_key = ?", (key,))
        conn.commit()
        conn.close()
        return len(bad)
    except Exception:
        return 0


TTL_GOLD_SILVER = 7200     # 2 hr
TTL_RISK_SENTIMENT = 900   # 15 min
TTL_USD_INDEX = 86400      # 24 hr
TTL_RATE_ENV = 3600        # 1 hr
TTL_WEEKLY = 604800        # 7 days
TTL_GEOPOLITICAL = 7200    # 2 hr
