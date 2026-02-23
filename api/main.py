import asyncio
from fastapi import FastAPI, Depends, Response, status
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import structlog

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from api.config import settings
from api.database import init_db, close_db, get_db
from api.logging_config import setup_logging
from api.services.firebase_push import init_firebase
from api.services.cache import cache
from api.services.storage import r2_client
from api.middleware.correlation import CorrelationIdMiddleware

# Import models so they are registered with Base.metadata
import api.models  # noqa: F401

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger.info("starting_svpms", env=settings.ENVIRONMENT)
    import os
    try:
        logger.info("checking_keys_dir", files=os.listdir("keys"), cwd=os.getcwd())
    except Exception as e:
        logger.error("keys_dir_check_failed", error=str(e))
    await init_db()
    init_firebase()
    yield
    await close_db()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url="/docs" if settings.DEBUG else None,
    lifespan=lifespan,
)

app.add_middleware(CorrelationIdMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_origin_regex=settings.CORS_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Idempotency-Key", "X-Requested-With", "X-Request-ID"],
)


@app.get("/health", tags=["System"])
async def health(response: Response, db: AsyncSession = Depends(get_db)):
    health_status = {"status": "healthy", "version": settings.APP_VERSION, "checks": {}}
    
    # 1. Check DB
    try:
        await db.execute(text("SELECT 1"))
        health_status["checks"]["db"] = "ok"
    except Exception as e:
        logger.error("health_check_db_failed", error=str(e))
        health_status["checks"]["db"] = "error"
        health_status["status"] = "unhealthy"
        
    # 2. Check Redis
    try:
        await cache.ping()
        health_status["checks"]["redis"] = "ok"
    except Exception as e:
        logger.error("health_check_redis_failed", error=str(e))
        health_status["checks"]["redis"] = "error"
        health_status["status"] = "unhealthy"
        
    # 3. Check R2
    try:
        await asyncio.to_thread(r2_client.s3.head_bucket, Bucket=r2_client.bucket)
        health_status["checks"]["r2"] = "ok"
    except Exception as e:
        logger.error("health_check_r2_failed", error=str(e))
        health_status["checks"]["r2"] = "error"
        health_status["status"] = "unhealthy"

    if health_status["status"] == "unhealthy":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return health_status


# --- Routers ---
from api.routes.auth import router as auth_router  # noqa: E402
from api.routes.departments import router as departments_router  # noqa: E402
from api.routes.users import router as users_router  # noqa: E402
from api.routes.budgets import router as budgets_router  # noqa: E402
from api.routes.vendors import router as vendors_router  # noqa: E402
from api.routes.purchase_requests import router as pr_router  # noqa: E402
from api.routes.purchase_orders import router as po_router  # noqa: E402
from api.routes.receipts import router as receipts_router  # noqa: E402
from api.routes.invoices import router as invoices_router  # noqa: E402
from api.routes.rfqs import router as rfqs_router  # noqa: E402
from api.routes.files import router as files_router  # noqa: E402
from api.routes.devices import router as devices_router  # noqa: E402
from api.routes.match import router as match_router  # noqa: E402
from api.jobs.scheduled import router as jobs_router  # noqa: E402
from api.routes.approvals import router as approvals_router  # noqa: E402
from api.routes.audit_logs import router as audit_logs_router  # noqa: E402

# Rate limiting middleware (Upstash Redis)
from api.middleware.rate_limit import rate_limit_middleware  # noqa: E402
app.middleware("http")(rate_limit_middleware)

app.include_router(auth_router, prefix="/auth", tags=["Auth"])
app.include_router(departments_router, prefix="/api/v1/departments", tags=["Departments"])
app.include_router(users_router, prefix="/api/v1/users", tags=["Users"])
app.include_router(budgets_router, prefix="/api/v1/budgets", tags=["Budgets"])
app.include_router(vendors_router, prefix="/api/v1/vendors", tags=["Vendors"])
app.include_router(pr_router, prefix="/api/v1/purchase-requests", tags=["Purchase Requests"])
app.include_router(po_router, prefix="/api/v1/purchase-orders", tags=["Purchase Orders"])
app.include_router(receipts_router, prefix="/api/v1/receipts", tags=["Receipts"])
app.include_router(invoices_router, prefix="/api/v1/invoices", tags=["Invoices"])
app.include_router(rfqs_router, prefix="/api/v1/rfqs", tags=["RFQs"])
app.include_router(files_router, prefix="/api/v1/files", tags=["Files"])
app.include_router(devices_router, prefix="/api/v1/users/me/devices", tags=["Devices"])
app.include_router(match_router, prefix="/api/v1/match", tags=["Matching"])
app.include_router(approvals_router, prefix="/api/v1/approvals", tags=["Approvals"])
app.include_router(audit_logs_router, prefix="/api/v1/audit-logs", tags=["Audit Logs"])
app.include_router(jobs_router, prefix="/internal/jobs", tags=["Internal Jobs"])
