# api/middleware/rate_limit.py
"""
Distributed rate limiting via Upstash Redis.
From 01_BACKEND.md §5.6.
"""

from fastapi import Request, HTTPException
from api.services.cache import cache
import structlog

logger = structlog.get_logger()

RATE_LIMITS = {
    "default": {"limit": 100, "window": 60},
    "auth": {"limit": 10, "window": 60},
    "upload": {"limit": 5, "window": 60},
}


def _get_limit_config(path: str) -> dict:
    """Determine rate limit config based on request path."""
    if path.startswith("/auth"):
        return RATE_LIMITS["auth"]
    if "/files/upload" in path:
        return RATE_LIMITS["upload"]
    return RATE_LIMITS["default"]


async def rate_limit_middleware(request: Request, call_next):
    """
    Rate limiting middleware using Upstash Redis.
    Tracks requests per IP + endpoint pattern with sliding window.
    """
    # Skip health check
    if request.url.path == "/health":
        return await call_next(request)

    # Use X-Forwarded-For when running behind a reverse proxy (Cloud Run, etc.)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # Take the first IP in the chain (the original client)
        client_ip = forwarded_for.split(",")[0].strip()
    else:
        client_ip = request.client.host if request.client else "unknown"
    config = _get_limit_config(request.url.path)
    limit = config["limit"]
    window = config["window"]

    # Build rate limit key
    key = f"rl:{client_ip}:{request.url.path}"

    try:
        current = await cache.incr(key)

        # Set TTL on first request in window
        if current == 1:
            await cache.expire(key, window)

        if current > limit:
            logger.warning(
                "rate_limited",
                ip=client_ip,
                path=request.url.path,
                current=current,
                limit=limit,
            )
            raise HTTPException(
                status_code=429,
                detail="Too many requests",
                headers={"Retry-After": str(window)},
            )

    except HTTPException:
        raise
    except Exception as e:
        # If Redis is down, allow the request (fail-open)
        logger.warning("rate_limit_cache_error", error=str(e))

    return await call_next(request)
