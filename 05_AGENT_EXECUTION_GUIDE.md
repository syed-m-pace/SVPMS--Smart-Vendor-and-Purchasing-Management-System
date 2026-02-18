# SVPMS Agent Execution Guide
## Step-by-Step Build, Run, Verify, and Deploy Commands

**Version:** 4.1 | **Purpose:** Deterministic execution plan for AI coding agents  
**Read 00_MANIFEST.md FIRST, then this file to understand the build order**

---

## EXECUTION PHILOSOPHY

This guide is designed for a **single AI agent** (or solo developer) building SVPMS iteratively. Each phase produces a runnable, testable increment. **Never build everything then test — build, run, verify, repeat.**

```
PHASE 1: Scaffold + Boot      →  "Hello World" on localhost:8000
PHASE 2: Auth + Users          →  Can login, get JWT, see /docs
PHASE 3: Core Entities (CRUD)  →  Vendors, PRs, POs, Budgets in DB
PHASE 4: Business Logic        →  Approval chains, budget locking, state machines
PHASE 5: Advanced Features     →  3-way matching, OCR, notifications, push
PHASE 6: Frontend Web          →  Next.js talking to local API
PHASE 7: Frontend Mobile       →  Flutter talking to local API
PHASE 8: Integration Testing   →  Full E2E flow locally
PHASE 9: Production Deploy     →  Cloud Run + Neon + R2 + Upstash
```

---

## PHASE 1: SCAFFOLD + BOOT (Est. 30 min)

### Goal: FastAPI runs on localhost:8000, connects to Neon Postgres, /health returns 200

```bash
# 1. Create project structure
mkdir -p svpms/{api/{routes,services,middleware,models,jobs},migrations/versions,tests/{unit,integration},keys,scripts}
cd svpms

# 2. Copy boilerplate files from 04_INFRASTRUCTURE.md §1
# Create these files verbatim:
#   requirements.txt       (§1.1)
#   .env                   (§1.2 — fill in YOUR Neon/Upstash/R2 credentials)
#   api/__init__.py        (empty)
#   api/config.py          (§1.4)
#   api/database.py        (§1.5)
#   api/main.py            (§1.6)
#   api/logging_config.py  (§1.7)
#   api/services/__init__.py         (empty)
#   api/services/firebase_push.py    (§6.1 from 04_INFRASTRUCTURE.md)
#   api/routes/__init__.py           (empty)
#   api/middleware/__init__.py        (empty)
#   api/models/__init__.py           (empty)
#   alembic.ini            (§1.8)
#   migrations/env.py      (§1.8)
#   migrations/versions/   (empty dir)

# 3. Install dependencies
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 4. Generate JWT key pair (required for auth later, create now to avoid startup errors)
openssl genrsa -out keys/private.pem 4096
openssl rsa -in keys/private.pem -pubout -out keys/public.pem

# 5. Set up Neon database
# Go to console.neon.tech, create project + database "svpms"
# Copy pooled connection string → .env DATABASE_URL
# Copy direct connection string → .env DATABASE_SYNC_URL
# Run extensions:
psql "YOUR_DIRECT_NEON_URL" -c 'CREATE EXTENSION IF NOT EXISTS "uuid-ossp"; CREATE EXTENSION IF NOT EXISTS "pgcrypto"; CREATE EXTENSION IF NOT EXISTS "pg_trgm";'

# 6. Run initial migration (creates all tables from 01_BACKEND.md §1)
# First create the initial migration with ALL DDL from 01_BACKEND.md §1.1-1.5
alembic revision --autogenerate -m "initial_schema"
# Review the generated migration, then:
alembic upgrade head

# 7. Boot the API
uvicorn api.main:app --reload --port 8000

# 8. VERIFY
curl http://localhost:8000/health
# Expected: {"status":"healthy","version":"1.0.0"}

curl http://localhost:8000/docs
# Expected: Swagger UI loads (in dev mode)
```

### ✅ Phase 1 Checklist
- [ ] `curl /health` returns `{"status":"healthy"}`
- [ ] Swagger UI at `/docs` loads
- [ ] No database connection errors in console
- [ ] Neon dashboard shows connections

---

## PHASE 2: AUTH + USERS (Est. 2-3 hours)

### Goal: Register user, login, get JWT, protected endpoints work

**Spec references:** `01_BACKEND.md` §2 (OpenAPI `/auth/*` endpoints), §7 (Validation), §8 (Roles)

```bash
# 1. Create SQLAlchemy models
# File: api/models/user.py
# - Map to `users` table DDL from 01_BACKEND.md §1.1
# - Map to `tenants` table
# - Map to `departments` table
# - Map to `user_devices` table (for FCM tokens later)

# 2. Create auth routes
# File: api/routes/auth.py
# Endpoints from 01_BACKEND.md §2 OpenAPI:
#   POST /auth/login      → validate credentials, return JWT access+refresh tokens
#   POST /auth/refresh     → refresh access token
#   POST /auth/register    → create tenant + admin user (first-time setup)

# 3. Create auth middleware
# File: api/middleware/auth.py
# - JWT RS256 verification using keys/public.pem
# - get_current_user dependency
# - require_roles decorator from 01_BACKEND.md §8

# 4. Create seed data script
# File: scripts/seed.py
# - Use seed data from 01_BACKEND.md §12
# - Creates test tenant, departments, users with known passwords

# 5. Run seed
python scripts/seed.py

# 6. Register routers in main.py (uncomment auth router)

# 7. VERIFY
# Login
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@acme.com","password":"SvpmsTest123!"}'
# Expected: {"access_token":"eyJ...", "refresh_token":"eyJ...", "user":{...}}

# Test protected endpoint
TOKEN="<paste access_token from above>"
curl http://localhost:8000/health \
  -H "Authorization: Bearer $TOKEN"
# Expected: 200 OK

# Test role-based access
curl http://localhost:8000/api/v1/vendors \
  -H "Authorization: Bearer $TOKEN"
# Expected: 401 (no vendor routes yet) or 200 empty list
```

### ✅ Phase 2 Checklist
- [ ] POST /auth/login returns JWT tokens
- [ ] POST /auth/refresh works
- [ ] Protected endpoints reject invalid tokens (401)
- [ ] Role in JWT claims matches user's role
- [ ] Seed data loads without errors

---

## PHASE 3: CORE ENTITIES CRUD (Est. 4-6 hours)

### Goal: Full CRUD for vendors, PRs, POs, invoices, budgets, departments

**Spec references:** `01_BACKEND.md` §2 (OpenAPI — all CRUD endpoints), §7 (Validation schemas)

**Build order** (dependencies flow downward):
```
departments → budgets → vendors → purchase_requests → pr_line_items
→ purchase_orders → po_line_items → receipts → invoices → invoice_line_items
→ payments → rfqs → rfq_bids
```

```bash
# For EACH entity, create:
# 1. SQLAlchemy model   (api/models/{entity}.py)      — from DDL in §1
# 2. Pydantic schema    (api/routes/schemas/{entity}.py) — from §7
# 3. CRUD route          (api/routes/{entity}.py)       — from OpenAPI §2
# 4. Register in main.py

# VERIFY after each entity:
# Create
curl -X POST http://localhost:8000/api/v1/vendors \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"legal_name":"Test Vendor","email":"v@test.com","tax_id":"GSTIN12345"}'

# List
curl http://localhost:8000/api/v1/vendors -H "Authorization: Bearer $TOKEN"

# Get by ID
curl http://localhost:8000/api/v1/vendors/{id} -H "Authorization: Bearer $TOKEN"

# Update
curl -X PUT http://localhost:8000/api/v1/vendors/{id} \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"legal_name":"Updated Name"}'

# Verify tenant isolation (login as different tenant user, should see empty list)
```

### ✅ Phase 3 Checklist
- [ ] All 12+ entity CRUD endpoints work
- [ ] Pagination works (page, limit, total)
- [ ] Validation rejects bad input (400 errors)
- [ ] Tenant isolation works (User A can't see User B's data)
- [ ] Swagger /docs shows all endpoints

---

## PHASE 4: BUSINESS LOGIC (Est. 6-8 hours)

### Goal: Approval chains, budget locking, state machines, notifications

**Spec references:** `01_BACKEND.md` §3 (Algorithms), §4 (State Machines), §5 (Background Jobs), §9 (Notifications)

```bash
# 1. Budget Check Service (§3.1)
# File: api/services/budget_service.py
# - Pessimistic locking (SELECT FOR UPDATE)
# - Budget reservation creation
# - Implements check_budget() algorithm exactly as specified

# 2. Approval Chain Service (§3.4)
# File: api/services/approval_service.py
# - Amount-based routing: <5k Manager, <25k +Finance Head, <100k +CFO
# - Self-approval prevention
# - Escalation timeouts (§5.4)

# 3. State Machine Engine (§4)
# File: api/services/state_machine.py
# - PR state machine (DRAFT→PENDING→APPROVED/REJECTED/CANCELLED)
# - PO state machine (DRAFT→SENT→ACKNOWLEDGED→FULFILLED→CLOSED)
# - Invoice state machine (UPLOADED→OCR_*→MATCHED/EXCEPTION→APPROVED→PAID)
# - Vendor state machine (DRAFT→PENDING_REVIEW→ACTIVE/BLOCKED/SUSPENDED)
# - RFQ state machine (DRAFT→OPEN→CLOSED→AWARDED)
# - Each transition runs guards and side effects as specified

# 4. Notification Service (§9)
# File: api/services/notification_service.py
# - Template registry from §9 TEMPLATE_REGISTRY
# - Email via Brevo (04_INFRASTRUCTURE.md §10)
# - Push via FCM (04_INFRASTRUCTURE.md §6)
# - Called as BackgroundTasks side effects from state transitions

# 5. Wire up submit/approve/reject endpoints
# - POST /api/v1/purchase-requests/{id}/submit → runs budget check + creates approvals
# - POST /api/v1/purchase-requests/{id}/approve → runs approval logic
# - POST /api/v1/purchase-requests/{id}/reject → rejects + releases budget

# VERIFY: Full approval flow
TOKEN_MANAGER=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"eng.manager@acme.com","password":"SvpmsTest123!"}' | jq -r .access_token)

# Create PR as procurement user
TOKEN_PROC=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"procurement@acme.com","password":"SvpmsTest123!"}' | jq -r .access_token)

PR_ID=$(curl -s -X POST http://localhost:8000/api/v1/purchase-requests \
  -H "Authorization: Bearer $TOKEN_PROC" \
  -H "Content-Type: application/json" \
  -d '{"description":"Test PR","department_id":"<eng_dept_id>","line_items":[{"description":"Laptops","quantity":5,"unit_price_cents":100000}]}' | jq -r .id)

# Submit PR
curl -X POST http://localhost:8000/api/v1/purchase-requests/$PR_ID/submit \
  -H "Authorization: Bearer $TOKEN_PROC"
# Expected: status=PENDING, budget reservation created

# Approve as manager
curl -X POST http://localhost:8000/api/v1/purchase-requests/$PR_ID/approve \
  -H "Authorization: Bearer $TOKEN_MANAGER" \
  -H "Content-Type: application/json" \
  -d '{"comments":"Approved"}'
# Expected: status=APPROVED (for amount <$5k, single approval needed)

# Check budget was updated
curl http://localhost:8000/api/v1/budgets -H "Authorization: Bearer $TOKEN_MANAGER"
# Expected: spent_cents increased or reservation committed
```

### ✅ Phase 4 Checklist
- [ ] Budget check with pessimistic locking works
- [ ] Approval chain routes to correct approvers based on amount
- [ ] Self-approval prevented
- [ ] PR state transitions: DRAFT→PENDING→APPROVED/REJECTED
- [ ] Budget reservation created on submit, released on reject
- [ ] Notification emails sent (check Brevo activity or logs)
- [ ] Concurrent budget requests don't cause overspend

---

## PHASE 5: ADVANCED FEATURES (Est. 4-6 hours)

### Goal: 3-way matching, OCR, file upload, push notifications, RFQ workflow

```bash
# 1. Three-Way Match Service (§3.2)
# File: api/services/three_way_match.py
# - Quantity check (zero tolerance)
# - Price check (2% tolerance, configurable)
# - Returns exceptions list or MATCHED

# 2. File Upload (04_INFRASTRUCTURE.md §3.2)
# - Upload to R2, store key in DB

# 3. Invoice OCR Worker (01_BACKEND.md §5.2)
# - Google Document AI integration
# - Runs as BackgroundTask after invoice upload
# - Auto-triggers 3-way match

# 4. FCM Push Notifications
# File: api/services/push_service.py (from 04_INFRASTRUCTURE.md §6.2)
# File: api/routes/devices.py (from 04_INFRASTRUCTURE.md §6.3)
# - Register device tokens from Flutter app
# - Send push on approval requests, exceptions, etc.

# 5. RFQ Workflow (§4 RFQ State Machine)
# - Create RFQ → Invite vendors → Receive bids → Score → Award

# 6. Scheduled Jobs (§5.4)
# - Document expiry checker
# - Approval timeout escalation
# - Budget utilization alerts

# VERIFY: Full invoice flow
# Upload invoice → OCR → 3-way match
curl -X POST http://localhost:8000/api/v1/invoices \
  -H "Authorization: Bearer $TOKEN_VENDOR" \
  -F "file=@test_invoice.pdf" \
  -F "po_id=$PO_ID"
# Expected: Invoice created, OCR queued, match runs automatically

# Check push notification device registration
curl -X POST http://localhost:8000/api/v1/users/me/devices \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"fcm_token":"test_token_123","device_type":"android","device_name":"Test Phone"}'
# Expected: 201 Created
```

### ✅ Phase 5 Checklist
- [ ] File upload to R2 works, presigned URL accessible
- [ ] Invoice OCR extracts fields via Google Document AI
- [ ] 3-way match produces correct results
- [ ] Device token registration works
- [ ] Push notification sends (verify in Firebase Console)
- [ ] RFQ create → bid → award flow works

---

## PHASE 6: FRONTEND WEB (Est. 6-8 hours)

### Goal: Next.js app talks to local API, all core screens functional

**Spec reference:** `02_FRONTEND_WEB.md`

```bash
# 1. Create Next.js project
cd svpms
npx create-next-app@14 web --typescript --tailwind --app --src-dir
cd web

# 2. Install dependencies (from 02_FRONTEND_WEB.md §1.1)
npm install zustand @tanstack/react-query react-hook-form zod @hookform/resolvers
npm install axios date-fns lucide-react
npx shadcn-ui@latest init

# 3. Build in this order (from 02_FRONTEND_WEB.md):
#   a. API client + auth store     (§6, §5)
#   b. Login page                  (§7)
#   c. Layout + navigation         (§4 middleware + role-based nav)
#   d. Dashboard                   (§3.1)
#   e. Vendor list + detail        (§3.2)
#   f. PR form + list              (§3.3)
#   g. Invoice exception resolver  (§3.4)
#   h. Approval dashboard          (Complete Implementations §1.2)

# 4. Configure API proxy
# In next.config.js:
# rewrites: async () => [{ source: '/api/:path*', destination: 'http://localhost:8000/api/:path*' }]

# 5. Run
npm run dev  # localhost:3000

# VERIFY:
# - Open http://localhost:3000
# - Login with admin@acme.com / SvpmsTest123!
# - Dashboard loads with data from API
# - Can create a vendor, create a PR, submit for approval
# - Role-based navigation shows correct items per role
```

### ✅ Phase 6 Checklist
- [ ] Login/logout works with JWT
- [ ] Dashboard shows real data from API
- [ ] Vendor CRUD works end-to-end
- [ ] PR creation with line items works
- [ ] PR approval flow works (submit → approve)
- [ ] Role-based nav hides unauthorized items
- [ ] Forms validate with Zod schemas

---

## PHASE 7: FRONTEND MOBILE (Est. 6-8 hours)

### Goal: Flutter app connects to local API, core screens functional, push notifications work

**Spec reference:** `03_FRONTEND_MOBILE.md`

```bash
# 1. Create Flutter project
cd svpms
flutter create --org com.svpms --platforms android,ios mobile
cd mobile

# 2. Add dependencies (from 03_FRONTEND_MOBILE.md §1.1 pubspec.yaml)
# flutter pub add dio flutter_bloc hive hive_flutter firebase_core firebase_messaging
# flutter pub add flutter_local_notifications go_router flutter_secure_storage

# 3. Firebase setup
# - Firebase Console → Create project → Add Android/iOS apps
# - Download google-services.json (Android) / GoogleService-Info.plist (iOS)
# - Place in android/app/ and ios/Runner/ respectively
# - flutterfire configure

# 4. Build in this order (from 03_FRONTEND_MOBILE.md):
#   a. API client (Dio + interceptors)
#   b. Auth BLoC + login screen
#   c. Push notification service (§8 — register token on login)
#   d. Dashboard screen
#   e. PO list + detail (vendor view)
#   f. Approval screen (manager view)
#   g. Invoice upload (camera + file picker)

# 5. Run on emulator
# Point API_BASE_URL to your machine's IP (not localhost):
# Android emulator: http://10.0.2.2:8000
# iOS simulator: http://localhost:8000
flutter run

# VERIFY:
# - Login works
# - FCM token registered (check /api/v1/users/me/devices)
# - Dashboard loads
# - Can view POs (as vendor)
# - Can approve PRs (as manager)
# - Push notification received when PR needs approval
```

### ✅ Phase 7 Checklist
- [ ] Login returns JWT, stored securely
- [ ] FCM device token registered to backend on login
- [ ] Dashboard loads real data
- [ ] Vendor can view their POs
- [ ] Manager can approve/reject from mobile
- [ ] Push notification received (test via Firebase Console → send test message)
- [ ] Offline → online sync works (Hive cache)

---

## PHASE 8: INTEGRATION TESTING (Est. 3-4 hours)

### Goal: Full end-to-end procurement flow verified locally

```bash
# Run the full happy path:
# 1. Admin creates vendor → ACTIVE
# 2. Procurement creates PR with line items
# 3. PR submitted → budget reserved → approval created
# 4. Manager approves → PR APPROVED
# 5. PO auto-created from PR → sent to vendor
# 6. Vendor acknowledges PO (mobile)
# 7. Goods received → Receipt created
# 8. Vendor uploads invoice (mobile or web)
# 9. OCR runs → 3-way match → MATCHED
# 10. Finance approves payment → Stripe PaymentIntent
# 11. Budget spent_cents updated

# Run automated tests
cd svpms
pytest tests/ -v --cov=api --cov-report=html

# Check coverage
open htmlcov/index.html
# Target: >80% line coverage

# Test tenant isolation specifically
pytest tests/security/test_tenant_isolation.py -v

# Test concurrent budget access
pytest tests/unit/test_budget_service.py -v -k "concurrent"

# Test edge cases from 01_BACKEND.md §10
pytest tests/unit/test_edge_cases.py -v
```

### ✅ Phase 8 Checklist
- [ ] Full PR→PO→Receipt→Invoice→Payment flow works
- [ ] Tenant isolation verified (cross-tenant access blocked)
- [ ] Budget concurrency safe (no overspend under load)
- [ ] 3-way match catches quantity/price mismatches
- [ ] Approval escalation works for different amounts
- [ ] Push notifications fire at correct trigger points
- [ ] Test coverage ≥80%
- [ ] No critical/high security issues

---

## PHASE 9: PRODUCTION DEPLOY (Est. 2-3 hours)

### Goal: System running on Cloud Run, accessible via public URL

**Only proceed after Phase 8 passes all checks.**

```bash
# 1. Create Google Cloud project
gcloud projects create svpms-prod --name="SVPMS Production"
gcloud config set project svpms-prod
gcloud services enable run.googleapis.com secretmanager.googleapis.com cloudscheduler.googleapis.com

# 2. Store secrets in Secret Manager
echo -n "postgresql+asyncpg://..." | gcloud secrets create neon-database-url --data-file=-
echo -n "postgresql+psycopg2://..." | gcloud secrets create neon-database-sync-url --data-file=-
echo -n "AXxxxx" | gcloud secrets create upstash-redis-token --data-file=-
echo -n "your_brevo_api_key..." | gcloud secrets create brevo-api-key --data-file=-
echo -n "your_stripe_secret_key" | gcloud secrets create stripe-secret-key --data-file=-
echo -n "whsec_xxx" | gcloud secrets create stripe-webhook-secret --data-file=-
echo -n "your_32_byte_key" | gcloud secrets create encryption-key --data-file=-
echo -n "your_r2_secret" | gcloud secrets create r2-secret-key --data-file=-
cat keys/firebase-service-account.json | gcloud secrets create firebase-service-account-json --data-file=-
cat keys/private.pem | gcloud secrets create jwt-private-key --data-file=-
cat keys/public.pem | gcloud secrets create jwt-public-key --data-file=-

# 3. Run Alembic migration against production Neon
DATABASE_SYNC_URL="your_prod_neon_direct_url" alembic upgrade head

# 4. Seed production data (optional — admin user only)
ENVIRONMENT=production DATABASE_URL="your_prod_url" python scripts/seed.py --admin-only

# 5. Build and deploy API
gcloud builds submit --tag gcr.io/svpms-prod/svpms-api
gcloud run deploy svpms-api \
  --image gcr.io/svpms-prod/svpms-api \
  --region us-central1 \
  --min-instances 1 --max-instances 10 \
  --memory 512Mi --cpu 1 \
  --set-env-vars "ENVIRONMENT=production,USE_SECRET_MANAGER=true,GCP_PROJECT_ID=svpms-prod"

# 6. Set up Cloud Scheduler (from 04_INFRASTRUCTURE.md §7)
# ... (commands from that section)

# 7. Deploy frontend
cd web
# Update API URL in .env.production to Cloud Run URL
npm run build
# Deploy to Vercel/Cloudflare Pages/Cloud Run

# 8. VERIFY PRODUCTION
API_URL=$(gcloud run services describe svpms-api --region us-central1 --format='value(status.url)')
curl $API_URL/health
# Expected: {"status":"healthy","env":"production"}

# Test login
curl -X POST $API_URL/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@acme.com","password":"<prod_password>"}'
```

### ✅ Phase 9 Checklist
- [ ] Cloud Run service healthy
- [ ] API responds on production URL
- [ ] Auth works with production secrets
- [ ] Database connected (Neon production)
- [ ] R2 file upload works
- [ ] Email notifications send (Brevo)
- [ ] Push notifications work (FCM)
- [ ] Cloud Scheduler jobs created and firing
- [ ] CORS configured for production frontend domain
- [ ] Swagger /docs is DISABLED in production

---

## AGENT QUICK REFERENCE

### File → Module Mapping

| PRD Section | Generates These Files |
|---|---|
| `01_BACKEND.md` §1 (Data Model) | `api/models/*.py`, `migrations/versions/001_initial.py` |
| `01_BACKEND.md` §2 (OpenAPI) | `api/routes/*.py`, `api/routes/schemas/*.py` |
| `01_BACKEND.md` §3 (Algorithms) | `api/services/budget_service.py`, `api/services/three_way_match.py`, `api/services/rfq_scoring.py`, `api/services/approval_service.py` |
| `01_BACKEND.md` §4 (State Machines) | `api/services/state_machine.py` |
| `01_BACKEND.md` §5 (Background Jobs) | `api/jobs/*.py` |
| `01_BACKEND.md` §6 (Errors) | `api/exceptions.py` |
| `01_BACKEND.md` §7 (Validation) | `api/routes/schemas/*.py` (Pydantic side) |
| `01_BACKEND.md` §8 (Roles) | `api/middleware/auth.py` (require_roles decorator) |
| `01_BACKEND.md` §9 (Notifications) | `api/services/notification_service.py`, `api/services/notification_templates.py` |
| `01_BACKEND.md` §11 (Tests) | `tests/unit/*.py`, `tests/integration/*.py` |
| `01_BACKEND.md` §12 (Seed) | `scripts/seed.py`, `tests/constants.py` |
| `02_FRONTEND_WEB.md` | `web/src/**/*.tsx`, `web/src/**/*.ts` |
| `03_FRONTEND_MOBILE.md` | `mobile/lib/**/*.dart` |
| `04_INFRASTRUCTURE.md` §1 | Root config files: `requirements.txt`, `.env`, `Dockerfile`, etc. |
| `04_INFRASTRUCTURE.md` §3 | `api/services/storage.py` |
| `04_INFRASTRUCTURE.md` §4 | `api/services/cache.py` |
| `04_INFRASTRUCTURE.md` §5 | `api/services/secrets.py` |
| `04_INFRASTRUCTURE.md` §6 | `api/services/firebase_push.py`, `api/services/push_service.py`, `api/routes/devices.py` |
| `04_INFRASTRUCTURE.md` §9 | `.github/workflows/deploy.yml` |

### Expected Final Project Structure

```
svpms/
├── api/
│   ├── __init__.py
│   ├── config.py
│   ├── database.py
│   ├── main.py
│   ├── logging_config.py
│   ├── exceptions.py
│   ├── middleware/
│   │   ├── auth.py
│   │   └── rate_limit.py
│   ├── models/
│   │   ├── __init__.py       # Import all models
│   │   ├── tenant.py
│   │   ├── user.py
│   │   ├── department.py
│   │   ├── budget.py
│   │   ├── vendor.py
│   │   ├── purchase_request.py
│   │   ├── purchase_order.py
│   │   ├── invoice.py
│   │   ├── receipt.py
│   │   ├── rfq.py
│   │   ├── approval.py
│   │   ├── audit_log.py
│   │   ├── payment.py
│   │   └── user_device.py
│   ├── routes/
│   │   ├── auth.py
│   │   ├── devices.py
│   │   ├── vendors.py
│   │   ├── purchase_requests.py
│   │   ├── purchase_orders.py
│   │   ├── invoices.py
│   │   ├── receipts.py
│   │   ├── budgets.py
│   │   ├── rfqs.py
│   │   ├── payments.py
│   │   ├── files.py
│   │   └── schemas/
│   │       ├── vendor.py
│   │       ├── purchase_request.py
│   │       └── ... (one per entity)
│   ├── services/
│   │   ├── budget_service.py
│   │   ├── approval_service.py
│   │   ├── three_way_match.py
│   │   ├── rfq_scoring.py
│   │   ├── state_machine.py
│   │   ├── notification_service.py
│   │   ├── notification_templates.py
│   │   ├── firebase_push.py
│   │   ├── push_service.py
│   │   ├── storage.py
│   │   ├── cache.py
│   │   ├── secrets.py
│   │   ├── email_service.py
│   │   ├── payments.py
│   │   ├── ocr.py
│   │   └── audit.py
│   └── jobs/
│       ├── invoice_ocr.py
│       ├── three_way_match.py
│       └── scheduled.py
├── migrations/
│   ├── env.py
│   └── versions/
├── tests/
│   ├── conftest.py
│   ├── constants.py
│   ├── unit/
│   └── integration/
├── scripts/
│   └── seed.py
├── keys/
│   ├── private.pem
│   ├── public.pem
│   └── firebase-service-account.json
├── web/                    # Next.js (Phase 6)
├── mobile/                 # Flutter (Phase 7)
├── .env
├── .env.production
├── .dockerignore
├── .github/workflows/deploy.yml
├── alembic.ini
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md
```

### Estimated LOC Output

| Component | Files | Lines |
|-----------|-------|-------|
| Backend (Python) | ~35 | ~8,000 |
| Frontend Web (TypeScript/React) | ~25 | ~5,000 |
| Frontend Mobile (Dart/Flutter) | ~20 | ~4,000 |
| Tests | ~15 | ~3,000 |
| Config/Infra | ~10 | ~500 |
| **Total** | **~105** | **~20,500** |

---

**END OF AGENT EXECUTION GUIDE** | Build incrementally. Verify each phase. Never skip tests.
