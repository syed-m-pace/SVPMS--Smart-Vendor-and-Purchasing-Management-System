# api/middleware/idempotency.py
"""
Idempotency-Key deduplication for financial mutation endpoints.

Clients send an `Idempotency-Key` header (UUID) on POST requests.
The middleware:
  1. On first request: processes normally and caches the response in Redis (24h TTL).
  2. On replay: returns the cached response without re-executing the handler.

Only applied to POST endpoints under /api/v1/ to protect financial operations.
GET, PATCH, DELETE requests are exempt (already safe to replay or idempotent by nature).
"""

import json

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import structlog

from api.services.cache import cache

logger = structlog.get_logger()

_IDEMPOTENCY_TTL = 86_400  # 24 hours
_LOCK_TTL = 30  # 30 seconds — prevent concurrent duplicate requests
_APPLICABLE_PATHS_PREFIX = "/api/v1/"


class IdempotencyMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):
        # Only intercept POST requests to API endpoints
        if request.method != "POST" or not request.url.path.startswith(_APPLICABLE_PATHS_PREFIX):
            return await call_next(request)

        idempotency_key = request.headers.get("Idempotency-Key")
        if not idempotency_key:
            return await call_next(request)

        # Scope key to tenant if available (prevent cross-tenant replay)
        tenant_id = request.headers.get("X-Tenant-ID", "global")
        cache_key = f"idempotency:{tenant_id}:{idempotency_key}"
        lock_key = f"idempotency_lock:{tenant_id}:{idempotency_key}"

        try:
            # Check for cached response
            cached = await cache.get(cache_key)
            if cached:
                logger.info(
                    "idempotency_cache_hit",
                    key=idempotency_key,
                    path=request.url.path,
                )
                payload = json.loads(cached)
                return JSONResponse(
                    status_code=payload["status_code"],
                    content=payload["body"],
                    headers={"X-Idempotent-Replayed": "true"},
                )

            # Acquire a short-lived lock to prevent concurrent duplicate requests
            acquired = await cache.setnx(lock_key, "1", ex=_LOCK_TTL)
            if not acquired:
                return JSONResponse(
                    status_code=409,
                    content={
                        "error": {
                            "code": "CONCURRENT_REQUEST",
                            "message": "A request with this Idempotency-Key is already being processed",
                        }
                    },
                )

        except Exception as e:
            logger.warning("idempotency_cache_check_failed", error=str(e))
            return await call_next(request)

        # Process the request
        response = await call_next(request)

        # Cache successful (2xx) and client-error (4xx) responses.
        # Do NOT cache 5xx — let the client retry.
        if response.status_code < 500:
            try:
                body_bytes = b""
                async for chunk in response.body_iterator:
                    body_bytes += chunk

                body_text = body_bytes.decode("utf-8")
                try:
                    body_json = json.loads(body_text)
                except ValueError:
                    body_json = {"raw": body_text}

                payload = json.dumps({
                    "status_code": response.status_code,
                    "body": body_json,
                })
                await cache.set(cache_key, payload, _IDEMPOTENCY_TTL)

                # Release lock
                await cache.delete(lock_key)

                return JSONResponse(
                    status_code=response.status_code,
                    content=body_json,
                    headers=dict(response.headers),
                )
            except Exception as e:
                logger.warning("idempotency_cache_store_failed", error=str(e))

        try:
            await cache.delete(lock_key)
        except Exception:
            pass

        return response
