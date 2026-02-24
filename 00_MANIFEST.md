# SVPMS AI-Executable PRD v4.1
## Solo-Optimized Agentic Specification Package

**Version:** 4.1 | **Date:** February 16, 2026 | **AI-Executability:** 95%

---

## AGENT INSTRUCTIONS

**You are generating a complete multi-tenant procurement SaaS system.** Read files in this exact order:

| # | File | Contents |
|---|------|----------|
| 1 | `00_MANIFEST.md` | THIS FILE — stack, glossary, cross-references |
| 2 | `05_AGENT_EXECUTION_GUIDE.md` | **READ SECOND** — 10-phase build plan with verify steps |
| 3 | `01_BACKEND.md` | DDL (23 tables), API (OpenAPI 40+ endpoints), algorithms, state machines, errors, validation, RBAC, notifications, edge cases, tests, seed data |
| 4 | `02_FRONTEND_WEB.md` | Next.js 14 Admin Portal — components, Zustand stores, routing, API client |
| 5 | `03_FRONTEND_MOBILE.md` | Flutter 3.16 Vendor Mobile — screens, BLoC, Dio client, FCM push client |
| 6 | `04_INFRASTRUCTURE.md` | All boilerplate, Neon/R2/Upstash/FCM server-side/Secrets, Docker, CI/CD |
| 7 | `06_FRONTEND_VENDOR_WEB.md` | Next.js 14 Vendor Web Portal — pages, components, API client, deployment |

**Core Rules:**
- All money as `BIGINT` cents, never floats
- All IDs are UUIDs
- All tables have `tenant_id` + PostgreSQL RLS
- All timestamps UTC
- Currency default: `INR`
- **Unified UI/UX**: Web and Mobile FE must share similar UI and color schemes, following modern design philosophy (avoid distinct visual identities).

---

## TECH STACK (ACTIVE)

```
┌─────────────────────────────────────────────────────┐
│                    CLIENT LAYER                       │
│  Next.js 14 Admin (web/) │ Next.js 14 Vendor (vendor-web/) │
│  Flutter 3.16 (mobile/)  │ Tailwind + shadcn/ui + Zustand  │
│  BLoC + Dio + FCM        │                                  │
└──────────────┬──────────────────────┬────────────────┘
               │         HTTPS        │
┌──────────────▼──────────────────────▼────────────────┐
│              GOOGLE CLOUD RUN (prod)                  │
│              localhost:8000 (dev)                      │
│  FastAPI 0.104+ (Python 3.11, async)                 │
│  SQLAlchemy 2.0 async │ Pydantic 2.5                 │
│  JWT RS256 auth        │ BackgroundTasks (in-process) │
│  Firebase Admin SDK    │ In-memory rate limiter       │
└──────┬──────────┬──────────┬─────────────────────────┘
       │          │          │
┌──────▼───┐ ┌───▼────┐ ┌──▼──────────────────────────┐
│  Neon    │ │  R2    │ │  Google Secret Manager       │
│ Postgres │ │ (R2)  │ │  (prod only)                 │
│serverless│ │ docs   │ │                              │
└──────────┘ └────────┘ └──────────────────────────────┘
```

| Component | Technology | Status |
|-----------|-----------|--------|
| Backend | FastAPI 0.104+ / Python 3.11 | ✅ ACTIVE |
| ORM | SQLAlchemy 2.0 async | ✅ ACTIVE |
| Database | Neon Postgres (serverless) | ✅ ACTIVE |
| Storage | Cloudflare R2 (S3-compatible) | ✅ ACTIVE |
| Push Notifications | Firebase Admin SDK (server→FCM→Flutter) | ✅ ACTIVE |
| Background Jobs | FastAPI BackgroundTasks (in-process) | ✅ ACTIVE |
| Secrets (prod) | Google Secret Manager | ✅ ACTIVE |
| Hosting (prod) | Google Cloud Run | ✅ ACTIVE |
| Rate Limiting | In-memory (single instance) | ✅ ACTIVE (stub) |
| Frontend Web (Admin) | Next.js 14 + TypeScript + Tailwind + shadcn/ui (`web/`) | ✅ ACTIVE |
| Frontend Web (Vendor) | Next.js 14 + TypeScript + Tailwind + shadcn/ui (`vendor-web/`) | ✅ ACTIVE |
| Frontend Mobile (Vendor) | Flutter 3.16 + Dart + BLoC + Dio (`mobile/`) | ✅ ACTIVE |
| Email | Brevo (Direct API) | ✅ ACTIVE |
| Payments | **STUB** → Stripe when ready | ⏸️ DEFERRED |
| Cache/Redis | Upstash Redis (REST API) | ✅ ACTIVE |
| OCR | Google Document AI | ✅ ACTIVE |
| Monitoring | Cloud Run + structlog + Firebase Crashlytics (mobile) | ✅ ACTIVE |

---

## AGENTIC EXECUTION GUIDE

### Phase 0: Prerequisites (Human — 15 min)

```bash
# 1. Create Neon Postgres database
#    → console.neon.tech → New Project → Copy pooled + direct connection strings

# 2. Create Cloudflare R2 bucket
#    → dash.cloudflare.com → R2 → Create bucket "svpms-documents" → Create API token

# 3. Create Firebase project (for push notifications)
#    → console.firebase.google.com → Create project → Project Settings → Service Accounts → Generate key
#    → Save as keys/firebase-service-account.json

# 4. Generate JWT keys
chmod +x scripts/generate_keys.sh && ./scripts/generate_keys.sh

# 5. Fill in .env from .env.example with real values from steps 1-3
```

### Phase 1: Backend Core (Agent — read 01_BACKEND.md + 04_INFRASTRUCTURE.md)

**Goal:** Working FastAPI server with database, auth, and core CRUD endpoints.

```
STEP 1.1 — Scaffold project structure
  → Read 04_INFRASTRUCTURE.md §1.8 (directory structure)
  → Create all directories: api/, api/models/, api/routes/, api/services/, etc.
  → Copy verbatim: requirements.txt, .env.example, Dockerfile, docker-compose.yml, .gitignore, .dockerignore
  → Copy verbatim: api/config.py, api/database.py, api/main.py, api/logging_config.py
  → Copy verbatim: alembic.ini, migrations/env.py
  → Run: pip install -r requirements.txt

STEP 1.2 — Create SQLAlchemy ORM models
  → Read 01_BACKEND.md §1 (Complete DDL for all 22+ tables)
  → Create api/models/__init__.py with Base = declarative_base()
  → Create one model file per entity matching the DDL exactly
  → Include: tenants, users, departments, budgets, budget_reservations, vendors,
    vendor_documents, purchase_requests, pr_line_items, purchase_orders, po_line_items,
    invoices, invoice_line_items, receipts, receipt_line_items, rfqs, rfq_line_items,
    rfq_bids, approvals, audit_logs, payments
  → IMPORTANT: users table must include fcm_token TEXT column
  → Run: alembic revision --autogenerate -m "initial" && alembic upgrade head

STEP 1.3 — Create auth system
  → Read 01_BACKEND.md §2 (OpenAPI — /auth endpoints) + §5.6 (Auth Middleware)
  → Build: api/routes/auth.py (login, register, refresh, logout)
  → Build: api/middleware/auth.py (JWT RS256 verify, get_current_user dependency)
  → Build: api/middleware/tenant.py (set RLS context per-request)
  → Build: api/services/auth_service.py (password hashing, JWT generation)
  → Test: POST /auth/login returns valid JWT, GET /health works

STEP 1.4 — Create CRUD routes (one entity at a time)
  → Read 01_BACKEND.md §2 (OpenAPI spec — all endpoints for each entity)
  → Build in this order (each depends on the previous):
    1. api/routes/users.py (includes PUT /users/me/fcm-token)
    2. api/routes/departments.py
    3. api/routes/vendors.py + vendor_documents
    4. api/routes/budgets.py
    5. api/routes/purchase_requests.py (with line items)
    6. api/routes/approvals.py
    7. api/routes/purchase_orders.py (with line items)
    8. api/routes/receipts.py
    9. api/routes/invoices.py (with line items)
    10. api/routes/rfqs.py + bids
    11. api/routes/files.py (R2 upload/download)
    12. api/routes/reports.py (dashboard aggregations)
  → For each: implement list (paginated), get, create, update, delete
  → Apply: RLS tenant context, role-based auth decorators

STEP 1.5 — Implement business logic services
  → Read 01_BACKEND.md §3 (Algorithms) + §4 (State Machines)
  → Build: api/services/budget_service.py (pessimistic locking, reservation lifecycle)
  → Build: api/services/approval_service.py (chain routing by amount threshold)
  → Build: api/services/matching_service.py (3-way match: PO vs Receipt vs Invoice)
  → Build: api/services/rfq_service.py (bid scoring, deadline management)
  → Build: api/services/audit.py (create_audit_log helper)

STEP 1.6 — Wire up notifications + push
  → Read 01_BACKEND.md §9 (Notification Dispatch) + 04_INFRASTRUCTURE.md §4 (Firebase)
  → Copy: api/services/push_service.py (Firebase Admin SDK — verbatim from 04_INFRASTRUCTURE.md §4.1)
  → Copy: api/services/email_service.py (Brevo — from 04_INFRASTRUCTURE.md §10)
  → Build: api/services/notification_service.py (dispatch to Brevo + Firebase push)
  → Wire BackgroundTasks: on PR submit → notify approver, on approval → notify requester, etc.

STEP 1.7 — Create remaining stub services
  → Copy verbatim from 04_INFRASTRUCTURE.md §10:
    api/services/stubs/payment_stub.py
  → Real services already created:
    api/services/cache.py      (Upstash Redis — 04_INFRASTRUCTURE.md §4)
    api/services/ocr.py        (Google Document AI — 04_INFRASTRUCTURE.md §12)
    api/services/email_service.py (Brevo — 04_INFRASTRUCTURE.md §10)
  → Copy: api/middleware/rate_limit.py (uses Upstash Redis via cache.py)

STEP 1.8 — Seed data + scheduled jobs
  → Read 01_BACKEND.md §12 (Seed Data)
  → Build: scripts/seed.py (bootstrap tenants, users, departments, budgets, vendors)
  → Build: api/routes/internal_jobs.py (document expiry, approval timeout, budget alerts)
  → Run: python scripts/seed.py
  → Test: Login as seed user, create PR, approve it

✅ CHECKPOINT: Backend is running locally on localhost:8000
  → /health returns 200
  → /docs shows Swagger UI with all endpoints
  → Can login, create tenant data, submit PR, approve, create PO
  → Seed data loaded, Firebase push configured
```

### Phase 2: Frontend Web (Agent — read 02_FRONTEND_WEB.md)

**Goal:** Working Next.js admin portal connected to local backend.

```
STEP 2.1 — Scaffold Next.js project
  → Read 02_FRONTEND_WEB.md §1-2 (package.json, project structure)
  → npx create-next-app@14 web --typescript --tailwind --app
  → Install deps: shadcn/ui, zustand, react-hook-form, zod, axios
  → Configure: NEXT_PUBLIC_API_URL=http://localhost:8000

STEP 2.2 — Build auth flow
  → Read 02_FRONTEND_WEB.md §7 (Login Page) + §5 (Auth Store)
  → Build: Login page, JWT token management, auth middleware
  → Build: Zustand auth store (login, logout, refreshToken)
  → Build: API client with axios interceptors (auto-attach JWT, auto-refresh)

STEP 2.3 — Build core pages
  → Read 02_FRONTEND_WEB.md §3 (Component Specs) + Complete Implementations section
  → Build in order:
    1. Dashboard (KPI cards, recent PRs, pending approvals)
    2. Vendor list + detail + create/edit forms
    3. Purchase Request form (multi-line items, budget check)
    4. Approval dashboard (approve/reject actions)
    5. Purchase Order list + detail
    6. Invoice list + exception resolver
    7. Budget overview
    8. User/department management (admin only)

STEP 2.4 — Role-based navigation
  → Read 01_BACKEND.md §8 (Roles & Permissions — Frontend section)
  → Implement: Navigation visibility by role, route guards

✅ CHECKPOINT: Web frontend running on localhost:3000
  → Can login → see dashboard → create PR → approve PR → create PO
  → Role-based navigation works (admin sees everything, vendor sees limited)
```

### Phase 3: Frontend Mobile (Agent — read 03_FRONTEND_MOBILE.md)

**Goal:** Working Flutter app with push notifications connected to backend.

```
STEP 3.1 — Scaffold Flutter project
  → Read 03_FRONTEND_MOBILE.md §1-2 (pubspec.yaml, project structure)
  → flutter create mobile && cd mobile
  → Add deps: dio, flutter_bloc, firebase_messaging, hive, etc.

STEP 3.2 — Build core screens
  → Read 03_FRONTEND_MOBILE.md §3 (Screen Specifications)
  → Build: Login, Dashboard, PO list, PO detail, Invoice upload, Approval screen

STEP 3.3 — Wire Firebase push notifications
  → Read 03_FRONTEND_MOBILE.md §8 (Firebase Messaging Setup)
  → Configure: google-services.json (Android) / GoogleService-Info.plist (iOS)
  → On app start: register FCM token → PUT /api/v1/users/me/fcm-token
  → Handle foreground + background push messages

✅ CHECKPOINT: Mobile app running on emulator
  → Login → see POs → approve via push notification → upload invoice photo
```

### Phase 4: Integration Testing (Agent)

**Goal:** Verify full end-to-end workflow locally before any cloud deployment.

```
STEP 4.1 — Full workflow smoke test
  → Start: Backend (localhost:8000) + Frontend (localhost:3000)
  → Test this exact flow:
    1. Login as eng.manager@acme.com
    2. Create Purchase Request ($45,000, Engineering dept)
    3. System should: check budget → create reservation → create approval records
    4. Login as finance.head@acme.com → see pending approval → approve
    5. Login as cfo@acme.com → see pending approval → approve
    6. PR status should be APPROVED
    7. Create PO from approved PR → send to vendor
    8. Login as vendor@alphasupplies.com → see PO → acknowledge
    9. Create receipt (GRN)
    10. Upload invoice → run 3-way match → should MATCH
    11. Verify: budget reservation → spent, audit logs created

STEP 4.2 — Run automated tests
  → Read 01_BACKEND.md §11 (Testing Specifications)
  → Run: pytest tests/ -v --cov=api --cov-fail-under=70
  → Key test areas: budget locking, approval routing, 3-way matching, tenant isolation

STEP 4.3 — Edge case validation
  → Read 01_BACKEND.md §10 (Edge Cases)
  → Test: concurrent budget requests, partial receipts, self-approval prevention
```

### Phase 5: Production Deployment (Human + Agent)

**Only after Phase 4 passes.** See `04_INFRASTRUCTURE.md §8` for Cloud Run deploy commands.

```
STEP 5.1 — Set up Google Secret Manager with production secrets
STEP 5.2 — Build Docker image → push to GCR
STEP 5.3 — Deploy Cloud Run service (min-instances=1)
STEP 5.4 — Configure Cloud Scheduler for cron jobs
STEP 5.5 — Deploy frontend to Vercel (or Cloud Run)
STEP 5.6 — Configure production CORS, domain, SSL
```

---

## GLOSSARY

| Term | Definition |
|------|-----------|
| PR | Purchase Request — internal request to buy |
| PO | Purchase Order — legal doc sent to vendor |
| GRN | Goods Receipt Note — confirms delivery |
| RFQ | Request for Quotation — competitive bidding |
| 3-Way Match | Validate PO vs Receipt vs Invoice |
| RLS | Row-Level Security — Postgres auto-filters by tenant |
| Budget Reservation | Temporary hold on funds pending approval |
| OCR | Extract data from invoice PDFs via Google Document AI |
| STUB | Placeholder implementation that logs actions. Currently only Payments still uses a stub. |

---

## CROSS-REFERENCE MAP

| If you need... | Look in... | Section |
|---------------|-----------|---------|
| Table DDL / Schema | `01_BACKEND.md` | §1 |
| API endpoints | `01_BACKEND.md` | §2 |
| Budget/Matching/Approval algorithms | `01_BACKEND.md` | §3 |
| State machines (PR/PO/Invoice/Vendor/RFQ) | `01_BACKEND.md` | §4 |
| Background jobs | `01_BACKEND.md` | §5 |
| Error codes | `01_BACKEND.md` | §6 |
| Validation schemas (Zod + Pydantic) | `01_BACKEND.md` | §7 |
| Roles & RBAC | `01_BACKEND.md` | §8 |
| Notification dispatch | `01_BACKEND.md` | §9 |
| Edge cases | `01_BACKEND.md` | §10 |
| Tests | `01_BACKEND.md` | §11 |
| Seed data | `01_BACKEND.md` | §12 |
| React components | `02_FRONTEND_WEB.md` | All |
| Flutter screens + FCM client | `03_FRONTEND_MOBILE.md` | All |
| Boilerplate, Docker, Deploy, Services | `04_INFRASTRUCTURE.md` | All |
| Firebase server-side push | `04_INFRASTRUCTURE.md` | §4 |
| Service implementations (Brevo, Redis, OCR) | `04_INFRASTRUCTURE.md` | §4, §10, §12 |

---

**STATUS:** ✅ PRODUCTION-READY PRD | Begin Phase 0 → then hand Phase 1 to AI agent
