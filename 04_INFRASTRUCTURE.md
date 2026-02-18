# SVPMS Infrastructure Specification
## Cloud Run + Neon Postgres + Cloudflare R2 + Upstash Redis + FCM + Google Secret Manager

**Version:** 4.1 Solo-Optimized | **AI-Executability:** 100% — All files verbatim-copyable  
**Read 00_MANIFEST.md FIRST for tech stack context**

---

## TABLE OF CONTENTS

1. [Boilerplate Files](#1-boilerplate-files)
2. [Neon Postgres](#2-neon-postgres)
3. [Cloudflare R2 Storage](#3-cloudflare-r2)
4. [Upstash Redis (256MB)](#4-upstash-redis)
5. [Google Secret Manager](#5-google-secret-manager)
6. [Firebase Cloud Messaging (Server-Side)](#6-fcm-server-side)
7. [Cloud Run Deployment](#7-cloud-run)
8. [Docker](#8-docker)
9. [CI/CD (GitHub Actions)](#9-cicd)
10. [Brevo Email](#10-email)
11. [Stripe Payments](#11-payments)
12. [Google Document AI (OCR)](#12-ocr)
13. [Monitoring](#13-monitoring)
14. [Operations & DR](#14-operations)

---

## 1. BOILERPLATE FILES

### 1.1 requirements.txt

```text
# === Core Framework ===
fastapi==0.104.1
uvicorn[standard]==0.24.0
python-multipart==0.0.6
pydantic==2.5.3
pydantic-settings==2.1.0

# === Auth ===
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4

# === Database (Neon Postgres) ===
sqlalchemy[asyncio]==2.0.23
asyncpg==0.29.0
psycopg2-binary==2.9.9
alembic==1.13.0

# === Cloudflare R2 (S3-compatible) ===
boto3==1.34.11

# === HTTP Client (Upstash REST + general) ===
httpx==0.25.2

# === Google Cloud ===
google-cloud-secret-manager==2.18.1
google-cloud-documentai==2.24.0
google-cloud-logging==3.8.0

# === Firebase (Server-Side Push Notifications) ===
firebase-admin==6.4.0

# === Integrations ===
# sendgrid removed in favor of brevo (via httpx)
stripe==7.10.0

# === Monitoring ===
structlog==23.2.0

# === Security ===
cryptography==41.0.7

# === Testing ===
pytest==7.4.4
pytest-asyncio==0.23.3
pytest-cov==4.1.0
factory-boy==3.3.1

# === Utilities ===
python-dateutil==2.8.2
orjson==3.9.10
tenacity==8.2.3
```

### 1.2 .env (Local Development)

```env
# === Application ===
APP_NAME=SVPMS
APP_VERSION=1.0.0
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=DEBUG
PORT=8000

# === Neon Postgres (get from console.neon.tech) ===
DATABASE_URL=postgresql+asyncpg://user:pass@ep-xxxx-pooler.us-east-2.aws.neon.tech/svpms?sslmode=require
DATABASE_SYNC_URL=postgresql+psycopg2://user:pass@ep-xxxx.us-east-2.aws.neon.tech/svpms?sslmode=require
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=5
DB_POOL_RECYCLE=300

# === Upstash Redis (get from console.upstash.com) ===
UPSTASH_REDIS_REST_URL=https://xxxx.upstash.io
UPSTASH_REDIS_REST_TOKEN=AXxxxx

# === Cloudflare R2 ===
R2_ACCOUNT_ID=your_account_id
R2_ACCESS_KEY_ID=your_key
R2_SECRET_ACCESS_KEY=your_secret
R2_BUCKET_NAME=svpms-documents
R2_ENDPOINT_URL=https://your_account_id.r2.cloudflarestorage.com

# === Auth ===
JWT_PRIVATE_KEY_PATH=keys/private.pem
JWT_PUBLIC_KEY_PATH=keys/public.pem
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=30
ENCRYPTION_KEY=dev_only_32_byte_key_change_me!!

# === Firebase (download JSON from Firebase Console → Project Settings → Service Accounts) ===
FIREBASE_CREDENTIALS_PATH=keys/firebase-service-account.json

# === Brevo ===
BREVO_API_KEY=your_brevo_api_key_here
EMAIL_FROM_ADDRESS=noreply@svpms.local

# === Stripe (test keys) ===
STRIPE_SECRET_KEY=sk_test_xxx
STRIPE_WEBHOOK_SECRET=whsec_test_xxx

# === Google Cloud ===
GCP_PROJECT_ID=your-project
DOCUMENT_AI_PROCESSOR=projects/xxx/locations/us/processors/xxx

# === CORS ===
CORS_ORIGINS=http://localhost:3000,http://localhost:8080
```

### 1.3 api/config.py

```python
from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional

class Settings(BaseSettings):
    APP_NAME: str = "SVPMS"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"
    PORT: int = 8000

    DATABASE_URL: str = ""
    DATABASE_SYNC_URL: str = ""
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 5
    DB_POOL_RECYCLE: int = 300

    UPSTASH_REDIS_REST_URL: str = ""
    UPSTASH_REDIS_REST_TOKEN: str = ""

    R2_ACCOUNT_ID: str = ""
    R2_ACCESS_KEY_ID: str = ""
    R2_SECRET_ACCESS_KEY: str = ""
    R2_BUCKET_NAME: str = "svpms-documents"
    R2_ENDPOINT_URL: str = ""

    JWT_PRIVATE_KEY_PATH: Optional[str] = "keys/private.pem"
    JWT_PUBLIC_KEY_PATH: Optional[str] = "keys/public.pem"
    JWT_ALGORITHM: str = "RS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ENCRYPTION_KEY: str = ""

    FIREBASE_CREDENTIALS_PATH: Optional[str] = None
    GCP_PROJECT_ID: str = ""
    DOCUMENT_AI_PROCESSOR: Optional[str] = None
    USE_SECRET_MANAGER: bool = False

    BREVO_API_KEY: Optional[str] = None
    EMAIL_FROM_ADDRESS: str = "noreply@svpms.example.com"
    STRIPE_SECRET_KEY: Optional[str] = None
    STRIPE_WEBHOOK_SECRET: Optional[str] = None
    CORS_ORIGINS: str = "http://localhost:3000"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",")]

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    class Config:
        env_file = ".env"
        case_sensitive = True

@lru_cache()
def get_settings() -> Settings:
    return Settings()

settings = get_settings()
```

### 1.4 api/database.py

```python
from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text
from api.config import settings
import structlog

logger = structlog.get_logger()

class Base(DeclarativeBase):
    pass

engine: AsyncEngine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_recycle=settings.DB_POOL_RECYCLE,
    pool_pre_ping=True,
    echo=settings.DEBUG,
)

AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

async def set_tenant_context(session: AsyncSession, tenant_id: str):
    await session.execute(text("SET LOCAL app.current_tenant_id = :tid"), {"tid": tenant_id})

async def init_db():
    async with engine.begin() as conn:
        await conn.execute(text("SELECT 1"))
        logger.info("neon_db_connected")

async def close_db():
    await engine.dispose()
    logger.info("neon_db_disconnected")
```

### 1.5 api/main.py

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import structlog

from api.config import settings
from api.database import init_db, close_db
from api.logging_config import setup_logging
from api.services.firebase_push import init_firebase

logger = structlog.get_logger()

@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger.info("starting_svpms", env=settings.ENVIRONMENT)
    await init_db()
    init_firebase()
    yield
    await close_db()

app = FastAPI(
    title=settings.APP_NAME, version=settings.APP_VERSION,
    docs_url="/docs" if settings.DEBUG else None, lifespan=lifespan,
)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins_list,
    allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

@app.get("/health", tags=["System"])
async def health():
    return {"status": "healthy", "version": settings.APP_VERSION}

# from api.routes import auth, devices, vendors, purchase_requests, purchase_orders
# from api.routes import invoices, receipts, budgets, rfqs, payments
# app.include_router(auth.router, prefix="/auth", tags=["Auth"])
# app.include_router(devices.router, prefix="/api/v1", tags=["Devices"])
# ... etc
```

### 1.6 api/logging_config.py

```python
import structlog, logging
from api.config import settings

def setup_logging():
    renderer = structlog.dev.ConsoleRenderer() if settings.ENVIRONMENT == "development" else structlog.processors.JSONRenderer()
    structlog.configure(
        processors=[structlog.contextvars.merge_contextvars, structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"), renderer],
        wrapper_class=structlog.make_filtering_bound_logger(getattr(logging, settings.LOG_LEVEL)),
        logger_factory=structlog.PrintLoggerFactory(), cache_logger_on_first_use=True,
    )
```

### 1.7 alembic.ini + migrations/env.py

```ini
[alembic]
script_location = migrations
sqlalchemy.url = driver://user:pass@host/svpms
file_template = %%(rev)s_%%(slug)s
timezone = UTC
[loggers]
keys = root,sqlalchemy,alembic
[handlers]
keys = console
[formatters]
keys = generic
[logger_root]
level = WARN
handlers = console
[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine
[logger_alembic]
level = INFO
handlers =
qualname = alembic
[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic
[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
```

```python
# migrations/env.py
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool, text
from alembic import context
import os
from api.database import Base

config = context.config
database_url = os.getenv("DATABASE_SYNC_URL", config.get_main_option("sqlalchemy.url"))
config.set_main_option("sqlalchemy.url", database_url)
if config.config_file_name: fileConfig(config.config_file_name)
target_metadata = Base.metadata

def run_migrations_offline():
    context.configure(url=database_url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction(): context.run_migrations()

def run_migrations_online():
    connectable = engine_from_config(config.get_section(config.config_ini_section), prefix="sqlalchemy.", poolclass=pool.NullPool)
    with connectable.connect() as connection:
        connection.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'))
        connection.execute(text('CREATE EXTENSION IF NOT EXISTS "pgcrypto"'))
        connection.execute(text('CREATE EXTENSION IF NOT EXISTS "pg_trgm"'))
        connection.commit()
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction(): context.run_migrations()

if context.is_offline_mode(): run_migrations_offline()
else: run_migrations_online()
```

---

## 2. NEON POSTGRES

```bash
# 1. console.neon.tech → Create Project → Database "svpms"
# 2. Enable extensions:
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
# 3. Copy connection strings:
#    Pooled (app):    -pooler suffix    → DATABASE_URL
#    Direct (alembic): no pooler suffix → DATABASE_SYNC_URL
```

**Best Practices:** Always use pooler endpoint for app. Direct only for migrations. `pool_pre_ping=True` + `pool_recycle=300` for Neon idle disconnects. Use `neon branch create` for dev isolation.

---

## 3. CLOUDFLARE R2

```python
# api/services/storage.py
import boto3
from botocore.config import Config
from api.config import settings
import structlog
logger = structlog.get_logger()

class R2Client:
    def __init__(self):
        self.s3 = boto3.client("s3", endpoint_url=settings.R2_ENDPOINT_URL,
            aws_access_key_id=settings.R2_ACCESS_KEY_ID,
            aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
            config=Config(signature_version="s3v4"), region_name="auto")
        self.bucket = settings.R2_BUCKET_NAME

    def upload(self, file_bytes: bytes, key: str, content_type: str = "application/pdf") -> str:
        self.s3.put_object(Bucket=self.bucket, Key=key, Body=file_bytes, ContentType=content_type)
        return key

    def download(self, key: str) -> bytes:
        return self.s3.get_object(Bucket=self.bucket, Key=key)["Body"].read()

    def get_presigned_url(self, key: str, expires_in: int = 3600) -> str:
        return self.s3.generate_presigned_url("get_object", Params={"Bucket": self.bucket, "Key": key}, ExpiresIn=expires_in)

    def delete(self, key: str):
        self.s3.delete_object(Bucket=self.bucket, Key=key)

r2_client = R2Client()
```

---

## 4. UPSTASH REDIS (256MB)

**Memory Budget:** Rate limits (~5MB, 60s TTL) + Sessions (~20MB, 7d TTL) + Idempotency (~10MB, 24h TTL) + Hot cache (~30MB, 5min TTL) = ~65MB used, ~191MB headroom. **TTL EVERYTHING.**

```python
# api/services/cache.py
import httpx, json
from api.config import settings

class UpstashClient:
    def __init__(self):
        self.url = settings.UPSTASH_REDIS_REST_URL
        self.headers = {"Authorization": f"Bearer {settings.UPSTASH_REDIS_REST_TOKEN}"}

    async def get(self, key: str) -> str | None:
        async with httpx.AsyncClient() as c:
            r = await c.get(f"{self.url}/get/{key}", headers=self.headers)
            return r.json().get("result")

    async def set(self, key: str, value: str, ex: int = 300):
        async with httpx.AsyncClient() as c:
            await c.get(f"{self.url}/set/{key}/{value}/ex/{ex}", headers=self.headers)

    async def incr(self, key: str) -> int:
        async with httpx.AsyncClient() as c:
            r = await c.get(f"{self.url}/incr/{key}", headers=self.headers)
            return r.json().get("result", 0)

    async def pipeline(self, commands: list[list]) -> list:
        async with httpx.AsyncClient() as c:
            r = await c.post(f"{self.url}/pipeline", headers=self.headers, json=commands)
            return r.json()

    async def delete(self, key: str):
        async with httpx.AsyncClient() as c:
            await c.get(f"{self.url}/del/{key}", headers=self.headers)

cache = UpstashClient()
```

---

## 5. GOOGLE SECRET MANAGER

```python
# api/services/secrets.py
from google.cloud import secretmanager
from functools import lru_cache
from api.config import settings

_client = None
def _get_client():
    global _client
    if _client is None: _client = secretmanager.SecretManagerServiceClient()
    return _client

@lru_cache(maxsize=20)
def get_secret(secret_id: str) -> str:
    """Secrets: jwt-private-key, jwt-public-key, encryption-key, neon-database-url,
    upstash-redis-token, brevo-api-key, stripe-secret-key, r2-secret-key, firebase-service-account-json"""
    client = _get_client()
    name = f"projects/{settings.GCP_PROJECT_ID}/secrets/{secret_id}/versions/latest"
    return client.access_secret_version(name=name).payload.data.decode("UTF-8")

def load_production_secrets():
    import os
    if not settings.USE_SECRET_MANAGER: return
    os.environ["DATABASE_URL"] = get_secret("neon-database-url")
    os.environ["DATABASE_SYNC_URL"] = get_secret("neon-database-sync-url")
    os.environ["UPSTASH_REDIS_REST_TOKEN"] = get_secret("upstash-redis-token")
    os.environ["BREVO_API_KEY"] = get_secret("brevo-api-key")
    os.environ["STRIPE_SECRET_KEY"] = get_secret("stripe-secret-key")
    os.environ["ENCRYPTION_KEY"] = get_secret("encryption-key")
```

---

## 6. FIREBASE CLOUD MESSAGING (SERVER-SIDE)

### 6.1 Firebase Admin SDK Init

```python
# api/services/firebase_push.py
import firebase_admin
from firebase_admin import credentials, messaging
from api.config import settings
from api.services.secrets import get_secret
import json, structlog

logger = structlog.get_logger()
_initialized = False

def init_firebase():
    """Called once at startup from main.py lifespan."""
    global _initialized
    if _initialized: return
    try:
        if settings.USE_SECRET_MANAGER:
            cred = credentials.Certificate(json.loads(get_secret("firebase-service-account-json")))
        elif settings.FIREBASE_CREDENTIALS_PATH:
            cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
        else:
            logger.warning("firebase_not_configured"); return
        firebase_admin.initialize_app(cred)
        _initialized = True
        logger.info("firebase_initialized")
    except Exception as e:
        logger.error("firebase_init_failed", error=str(e))
```

### 6.2 Push Notification Service

```python
# api/services/push_service.py
from firebase_admin import messaging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import structlog

logger = structlog.get_logger()

async def send_push_notification(db: AsyncSession, user_ids: list[str], title: str, body: str, data: dict | None = None):
    """
    Send FCM push to users. Looks up device tokens, sends multicast, auto-deactivates stale tokens.
    """
    if not user_ids: return
    from api.models import UserDevice
    result = await db.execute(select(UserDevice).where(UserDevice.user_id.in_(user_ids), UserDevice.is_active == True))
    devices = result.scalars().all()
    if not devices:
        logger.info("push_no_devices", user_ids=user_ids); return

    tokens = [d.fcm_token for d in devices]
    message = messaging.MulticastMessage(
        notification=messaging.Notification(title=title, body=body),
        data={k: str(v) for k, v in (data or {}).items()},
        tokens=tokens,
        android=messaging.AndroidConfig(priority="high",
            notification=messaging.AndroidNotification(click_action="FLUTTER_NOTIFICATION_CLICK", channel_id="svpms_default")),
        apns=messaging.APNSConfig(payload=messaging.APNSPayload(aps=messaging.Aps(badge=1, sound="default"))),
    )
    try:
        response = messaging.send_each_for_multicast(message)
        logger.info("push_sent", success=response.success_count, failure=response.failure_count)
        # Deactivate invalid tokens
        if response.failure_count > 0:
            for i, sr in enumerate(response.responses):
                if sr.exception and sr.exception.code in ("NOT_FOUND", "UNREGISTERED", "INVALID_ARGUMENT"):
                    devices[i].is_active = False
            await db.commit()
    except Exception as e:
        logger.error("push_failed", error=str(e))
```

### 6.3 Device Token Registration API

```python
# api/routes/devices.py
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from api.database import get_db, set_tenant_context
from api.middleware.auth import get_current_user

router = APIRouter()

class DeviceRegisterRequest(BaseModel):
    fcm_token: str = Field(..., min_length=10, max_length=500)
    device_type: str = Field(..., pattern="^(android|ios|web)$")
    device_name: str | None = Field(None, max_length=200)

@router.post("/users/me/devices", status_code=201)
async def register_device(req: DeviceRegisterRequest, db: AsyncSession = Depends(get_db), user: dict = Depends(get_current_user)):
    """Register/update FCM token. Called on app start + onTokenRefresh."""
    await set_tenant_context(db, user["tenant_id"])
    from api.models import UserDevice
    existing = await db.execute(select(UserDevice).where(and_(UserDevice.user_id == user["user_id"], UserDevice.fcm_token == req.fcm_token)))
    device = existing.scalar_one_or_none()
    if device:
        device.is_active = True
        device.device_name = req.device_name or device.device_name
    else:
        device = UserDevice(user_id=user["user_id"], tenant_id=user["tenant_id"],
            fcm_token=req.fcm_token, device_type=req.device_type, device_name=req.device_name, is_active=True)
        db.add(device)
    await db.flush()
    return {"id": str(device.id), "device_type": device.device_type, "is_active": True}

@router.delete("/users/me/devices/{device_id}", status_code=204)
async def unregister_device(device_id: str, db: AsyncSession = Depends(get_db), user: dict = Depends(get_current_user)):
    """Deactivate device on logout."""
    await set_tenant_context(db, user["tenant_id"])
    from api.models import UserDevice
    device = await db.get(UserDevice, device_id)
    if not device or str(device.user_id) != user["user_id"]: raise HTTPException(404)
    device.is_active = False
```

### 6.4 NotificationService._send_push Integration

```python
# In api/services/notification_service.py, replace the _send_push stub:

async def _send_push(self, request):
    """Send push via FCM using firebase-admin SDK."""
    from api.services.push_service import send_push_notification
    from api.database import AsyncSessionLocal, set_tenant_context
    template = TEMPLATE_REGISTRY[request.template_id]
    title = template.get("push_title", template["subject"]).format(**request.context)
    body = template.get("push_body", "").format(**request.context)
    if not body: return
    async with AsyncSessionLocal() as db:
        await set_tenant_context(db, request.context.get("tenant_id", ""))
        await send_push_notification(db, request.recipient_user_ids, title, body,
            {"entity_type": request.entity_type or "", "entity_id": request.entity_id or ""})
```

---

## 7. CLOUD RUN

```bash
gcloud config set project PROJECT_ID
gcloud services enable run.googleapis.com secretmanager.googleapis.com cloudscheduler.googleapis.com

gcloud builds submit --tag gcr.io/PROJECT_ID/svpms-api
gcloud run deploy svpms-api --image gcr.io/PROJECT_ID/svpms-api --region us-central1 \
  --allow-unauthenticated --min-instances 1 --max-instances 10 --memory 512Mi --cpu 1 --timeout 300 \
  --set-env-vars "ENVIRONMENT=production,USE_SECRET_MANAGER=true,GCP_PROJECT_ID=PROJECT_ID"

# Cloud Scheduler cron jobs
URL=$(gcloud run services describe svpms-api --region us-central1 --format='value(status.url)')
gcloud scheduler jobs create http doc-expiry --schedule="0 9 * * *" --uri="$URL/internal/jobs/check-document-expiry" --http-method=POST --oidc-service-account-email=scheduler@PROJECT_ID.iam.gserviceaccount.com
gcloud scheduler jobs create http approval-timeout --schedule="0 */4 * * *" --uri="$URL/internal/jobs/check-approval-timeouts" --http-method=POST --oidc-service-account-email=scheduler@PROJECT_ID.iam.gserviceaccount.com
gcloud scheduler jobs create http budget-alert --schedule="0 8 * * 1" --uri="$URL/internal/jobs/budget-alerts" --http-method=POST --oidc-service-account-email=scheduler@PROJECT_ID.iam.gserviceaccount.com
```

---

## 8. DOCKER

### Dockerfile
```dockerfile
FROM python:3.11-slim AS builder
WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.11-slim
RUN groupadd -r svpms && useradd -r -g svpms -d /app svpms
WORKDIR /app
COPY --from=builder /install /usr/local
COPY . .
RUN mkdir -p /app/keys && chown -R svpms:svpms /app
USER svpms
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import httpx; httpx.get('http://localhost:8000/health').raise_for_status()"
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### docker-compose.yml (Local Dev Only)
```yaml
version: "3.9"
services:
  api:
    build: .
    ports: ["8000:8000"]
    volumes: [".:/app"]
    env_file: .env
    command: uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
  web:
    image: node:20-alpine
    working_dir: /app
    ports: ["3000:3000"]
    volumes: ["./web:/app"]
    command: sh -c "npm install && npm run dev"
```

### .dockerignore
```
.git
.env*
__pycache__
node_modules
web/
mobile/
keys/
*.md
tests/
```

---

## 9. CI/CD

### .github/workflows/deploy.yml
```yaml
name: SVPMS CI/CD
on:
  push: { branches: [main] }
  pull_request: { branches: [main] }
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - run: pip install -r requirements.txt
      - run: pytest tests/ -v --cov=api --cov-fail-under=80
        env:
          DATABASE_URL: ${{ secrets.NEON_TEST_DB }}
          UPSTASH_REDIS_REST_URL: ${{ secrets.UPSTASH_URL }}
          UPSTASH_REDIS_REST_TOKEN: ${{ secrets.UPSTASH_TOKEN }}
  deploy:
    needs: test
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: google-github-actions/auth@v2
        with: { workload_identity_provider: "${{ secrets.GCP_WIF }}", service_account: "${{ secrets.GCP_SA }}" }
      - run: gcloud builds submit --tag gcr.io/${{ secrets.GCP_PROJECT }}/svpms-api:${{ github.sha }}
      - run: gcloud run deploy svpms-api --image gcr.io/${{ secrets.GCP_PROJECT }}/svpms-api:${{ github.sha }} --region us-central1
```

---

## 10-12. INTEGRATIONS

### Brevo Email
```python
# api/services/email_service.py
from typing import List
import httpx
from api.config import settings
import structlog
logger = structlog.get_logger()

BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"

async def send_email(to_emails: List[str], subject: str, html_content: str, sender_name: str = settings.APP_NAME, sender_email: str = settings.EMAIL_FROM_ADDRESS):
    """Send email using Brevo (formerly Sendinblue) API via HTTPX."""
    if not settings.BREVO_API_KEY: logger.warning("brevo_api_key_missing"); return False
    if not to_emails: return False

    headers = {"accept": "application/json", "api-key": settings.BREVO_API_KEY, "content-type": "application/json"}
    payload = {
        "sender": {"name": sender_name, "email": sender_email},
        "to": [{"email": e} for e in to_emails],
        "subject": subject,
        "htmlContent": html_content
    }
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(BREVO_API_URL, headers=headers, json=payload, timeout=10.0)
            if resp.status_code in (201, 202): logger.info("email_sent", to=to_emails); return True
            else: logger.error("email_failed", status=resp.status_code, body=resp.text); return False
    except Exception as e: logger.error("email_exception", error=str(e)); return False
```

### Stripe Payments
```python
# api/services/payments.py
import stripe
from api.config import settings
stripe.api_key = settings.STRIPE_SECRET_KEY

def create_payment_intent(amount_cents: int, currency: str = "inr", metadata: dict = None):
    return stripe.PaymentIntent.create(amount=amount_cents, currency=currency.lower(), metadata=metadata or {})

def handle_webhook(payload: bytes, sig_header: str):
    return stripe.Webhook.construct_event(payload, sig_header, settings.STRIPE_WEBHOOK_SECRET)
```

### Google Document AI (OCR)
```python
# api/services/ocr.py
from google.cloud import documentai_v1 as documentai
from api.config import settings

def extract_invoice_data(file_bytes: bytes) -> dict:
    client = documentai.DocumentProcessorServiceClient()
    result = client.process_document(request=documentai.ProcessRequest(
        name=settings.DOCUMENT_AI_PROCESSOR,
        raw_document=documentai.RawDocument(content=file_bytes, mime_type="application/pdf")))
    fields = {}
    for e in result.document.entities:
        if e.type_ == "invoice_id": fields["invoice_number"] = e.mention_text
        elif e.type_ == "total_amount": fields["total_cents"] = int(float(e.mention_text.replace(",","").replace("₹","")) * 100)
    fields["confidence"] = min((e.confidence for e in result.document.entities), default=0)
    return fields
```

---

## 13-14. MONITORING & OPS

Cloud Run built-in: request count, latency, CPU, memory. Use structured JSON logs (setup in §1.6) for Cloud Logging auto-ingestion.

**Cost Estimate (Solo):** Cloud Run $0-10 + Neon $0-19 + Upstash $0-10 + R2 $0-5 + Firebase FCM $0 + SecretMgr $0 + Brevo $0 = **$0-44/month**

**Backups:** Neon PITR (7d free), R2 multi-region, Upstash ephemeral (cache rebuilds on miss).

---

**END OF INFRASTRUCTURE** | ✅ COMPLETE | FCM server-side fully implemented
