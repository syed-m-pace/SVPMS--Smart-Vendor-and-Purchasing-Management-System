# api/middleware/rate_limit.py
"""
Distributed rate limiting via Upstash Redis.
Role-aware: privileged internal users get higher limits than vendor accounts.
From 01_BACKEND.md §5.6.
"""

import base64
import json

from fastapi import Request, HTTPException
from api.services.cache import cache
import structlog

logger = structlog.get_logger()

# Limits per (role_tier, path_category): {limit, window_seconds}
_TIER_LIMITS = {
    # admin / finance / cfo / procurement_lead
    "privileged": {
        "auth": {"limit": 20, "window": 60},
        "upload": {"limit": 20, "window": 60},
        "default": {"limit": 500, "window": 60},
    },
    # procurement / manager / finance
    "internal": {
        "auth": {"limit": 15, "window": 60},
        "upload": {"limit": 10, "window": 60},
        "default": {"limit": 200, "window": 60},
    },
    # vendor role or unauthenticated
    "vendor": {
        "auth": {"limit": 10, "window": 60},
        "upload": {"limit": 5, "window": 60},
        "default": {"limit": 60, "window": 60},
    },
}

_PRIVILEGED_ROLES = {"admin", "finance_head", "cfo", "procurement_lead"}
_INTERNAL_ROLES = {"procurement", "manager", "finance"}

SKIP_PATHS = {"/health"}
SKIP_PREFIXES = ("/internal/",)


def _extract_jwt_info(request: Request) -> tuple[str, str | None]:
    """
    Extract user role tier and user_id from JWT payload.
    Returns (tier, user_id) — user_id may be None for unauthenticated requests.
    Fails open — returns ('vendor', None) on any decode error.
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return "vendor", None
    try:
        token = auth_header.split(" ", 1)[1]
        payload_b64 = token.split(".")[1]
        # Add padding
        payload_b64 += "=" * (4 - len(payload_b64) % 4)
        payload = json.loads(base64.urlsafe_b64decode(payload_b64))
        role = payload.get("role", "")
        user_id = payload.get("sub") or payload.get("user_id")
        if role in _PRIVILEGED_ROLES:
            return "privileged", user_id
        if role in _INTERNAL_ROLES:
            return "internal", user_id
        return "vendor", user_id
    except Exception:
        return "vendor", None


def _get_path_category(path: str) -> str:
    if path.startswith("/auth"):
        return "auth"
    if "/files/upload" in path:
        return "upload"
    return "default"


async def rate_limit_middleware(request: Request, call_next):
    """
    Rate limiting middleware using Upstash Redis.
    Tracks requests per IP + endpoint pattern with sliding window.
    Internal job endpoints are skipped (they use Bearer token auth instead).
    """
    path = request.url.path
    if path in SKIP_PATHS or path.startswith(SKIP_PREFIXES):
        return await call_next(request)

    # Use X-Forwarded-For when running behind a reverse proxy (Cloud Run, etc.)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        client_ip = forwarded_for.split(",")[0].strip()
    else:
        client_ip = request.client.host if request.client else "unknown"

    tier, user_id = _extract_jwt_info(request)
    category = _get_path_category(path)
    config = _TIER_LIMITS[tier][category]
    limit = config["limit"]
    window = config["window"]

    # Use user_id for authenticated requests (prevents shared-IP blocking),
    # fall back to IP for unauthenticated endpoints
    identity = user_id or client_ip
    key = f"rl:{tier}:{identity}:{path}"

    try:
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
                tier=tier,
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
        logger.warning("rate_limit_cache_error", error=str(e))

    return await call_next(request)
