"""
app/redis_client.py — Redis connection for rate limiting and session caching.
Phase 2: Falls back to in-memory dict if Redis is unavailable (local dev).
"""

import os
import time
from collections import defaultdict

REDIS_URL = os.environ.get("REDIS_URL") or os.environ.get("REDIS_PRIVATE_URL")

_redis = None
_fallback_store: dict = defaultdict(dict)  # in-memory fallback


async def get_redis():
    """Get Redis client, or None if unavailable."""
    global _redis
    if _redis is not None:
        return _redis
    if not REDIS_URL:
        return None
    try:
        import redis.asyncio as aioredis
        _redis = await aioredis.from_url(REDIS_URL, decode_responses=True)
        await _redis.ping()
        print("[ REDIS ] Connected.")
        return _redis
    except Exception as e:
        print(f"[ REDIS ] Unavailable: {e} — using in-memory fallback.")
        return None


# ---------------------------------------------------------------------------
# RATE LIMITING
# ---------------------------------------------------------------------------

RATE_LIMITS = {
    "sovereign_per_hour": 5,
    "sovereign_per_day":  15,
    "quick_per_hour":     30,
}

TIER_LIMITS = {
    "free":       {"sovereign_per_day": 3,   "quick_per_day": 20},
    "pro":        {"sovereign_per_day": 50,  "quick_per_day": 500},
    "enterprise": {"sovereign_per_day": 999, "quick_per_day": 9999},
}


async def check_rate_limit(user_id: str, call_type: str, tier: str = "free") -> tuple[bool, str]:
    """
    Returns (allowed, reason).
    Uses Redis if available, falls back to in-memory store.
    """
    redis = await get_redis()
    now = int(time.time())
    hour_key = f"rate:{user_id}:{call_type}:hour:{now // 3600}"
    day_key  = f"rate:{user_id}:{call_type}:day:{now // 86400}"

    tier_config = TIER_LIMITS.get(tier, TIER_LIMITS["free"])

    if redis:
        try:
            hour_count = int(await redis.get(hour_key) or 0)
            day_count  = int(await redis.get(day_key) or 0)

            day_limit = tier_config.get(f"{call_type}_per_day", 10)
            hour_limit = RATE_LIMITS.get(f"{call_type}_per_hour", 10)

            if hour_count >= hour_limit:
                return False, f"Rate limit: max {hour_limit} {call_type.upper()} requests per hour."
            if day_count >= day_limit:
                return False, f"Daily limit reached. Upgrade to Pro for more requests."

            # Increment counters with TTL
            pipe = redis.pipeline()
            pipe.incr(hour_key)
            pipe.expire(hour_key, 3600)
            pipe.incr(day_key)
            pipe.expire(day_key, 86400)
            await pipe.execute()
            return True, ""

        except Exception as e:
            print(f"[ REDIS ] Rate limit error: {e} — allowing request.")
            return True, ""
    else:
        # In-memory fallback
        store = _fallback_store[user_id]
        hour_bucket = now // 3600
        day_bucket  = now // 86400

        h_key = f"{call_type}:h:{hour_bucket}"
        d_key = f"{call_type}:d:{day_bucket}"

        hour_count = store.get(h_key, 0)
        day_count  = store.get(d_key, 0)

        hour_limit = RATE_LIMITS.get(f"{call_type}_per_hour", 10)
        day_limit  = tier_config.get(f"{call_type}_per_day", 10)

        if hour_count >= hour_limit:
            return False, f"Rate limit: max {hour_limit} {call_type.upper()} requests per hour."
        if day_count >= day_limit:
            return False, f"Daily limit reached. Upgrade to Pro for more requests."

        store[h_key] = hour_count + 1
        store[d_key] = day_count + 1
        return True, ""


async def get_usage_stats(user_id: str) -> dict:
    """Returns current usage counts for a user."""
    redis = await get_redis()
    now = int(time.time())

    if redis:
        try:
            s_hour = int(await redis.get(f"rate:{user_id}:sovereign:hour:{now // 3600}") or 0)
            s_day  = int(await redis.get(f"rate:{user_id}:sovereign:day:{now // 86400}") or 0)
            q_hour = int(await redis.get(f"rate:{user_id}:quick:hour:{now // 3600}") or 0)
        except Exception:
            s_hour = s_day = q_hour = 0
    else:
        store = _fallback_store[user_id]
        s_hour = store.get(f"sovereign:h:{now // 3600}", 0)
        s_day  = store.get(f"sovereign:d:{now // 86400}", 0)
        q_hour = store.get(f"quick:h:{now // 3600}", 0)

    return {
        "sovereign_this_hour": s_hour,
        "sovereign_today":     s_day,
        "quick_this_hour":     q_hour,
        "limits":              RATE_LIMITS,
        "tier_limits":         TIER_LIMITS,
    }
