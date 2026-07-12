import time
import functools

_cache_store = {}

def cached_tool(ttl_seconds):
    """Decorator that caches a tool function's result for ttl_seconds.
    Place this BELOW @tool (i.e. closer to the function) so it wraps
    the raw function before LangChain's @tool wraps it."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            key = (func.__name__, args, tuple(sorted(kwargs.items())))
            now = time.time()
            if key in _cache_store:
                value, timestamp = _cache_store[key]
                if now - timestamp < ttl_seconds:
                    return value
            result = func(*args, **kwargs)
            _cache_store[key] = (result, now)
            return result
        return wrapper
    return decorator


TTL_GOLD_SILVER = 7200     # 2 hr
TTL_RISK_SENTIMENT = 900   # 15 min
TTL_USD_INDEX = 86400      # 24 hr
TTL_RATE_ENV = 3600        # 1 hr
TTL_WEEKLY = 604800        # 7 days
TTL_GEOPOLITICAL = 7200    # 2 hr