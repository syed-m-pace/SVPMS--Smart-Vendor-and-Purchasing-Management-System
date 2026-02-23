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

SKIP_PATHS = {"/health"}
SKIP_PREFIXES = ("/internal/",)


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
    Internal job endpoints are skipped (they use Bearer token auth instead).
    """
    # Skip health check and internal endpoints
    path = request.url.path
    if path in SKIP_PATHS or path.startswith(SKIP_PREFIXES):
        return await call_next(request)

    # Use X-Forwarded-For when running behind a reverse proxy (Cloud Run, etc.)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # Take the first IP in the chain (the original client)
        client_ip = forwarded_for.split(",")[0].strip()
    else:
        client_ip = request.client.host if request.client else "unknown"
    config = _get_limit_config(path)
    limit = config["limit"]
    window = config["window"]

    # Build rate limit key
    key = f"rl:{client_ip}:{path}"

    try:
        # Use a pipeline to combine INCR + EXPIRE into a single HTTP round-trip
        results = await cache.pipeline([
            ["INCR", key],
            ["EXPIRE", key, window],
        ])
        current = results[0].get("result", 0) if isinstance(results[0], dict) else 0

        if current > limit:
            logger.warning(
                "rate_limited",
                ip=client_ip,
                path=path,
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
