# SVPMS Project Memory

## Workflow Rules
- **Always update MEMORY.md** after completing phase planning and execution (status, new pitfalls, architecture decisions, file changes)
- **Always copy updated MEMORY.md** to `SVPMS_V4/MEMORY.md` to keep the public copy in sync

## Working Directory
- Backend code: `/Users/pacewisdom/Documents/svpms/SVPMS_V4/`
- All commands must run from this directory (venv is at `.venv/`)

## Key Pitfalls Encountered
- **asyncpg SSL**: `sslmode=require` in URL doesn't work with asyncpg. Must strip it from URL and pass `connect_args={"ssl": "require"}` to `create_async_engine()`.
- **Pydantic Settings extra fields**: `.env` has vars not in Settings class (e.g. FLUTTER_ANDROID_PROJECT_NAME). Must use `extra = "ignore"` in Config.
- **Circular FK departments<->users**: Alembic can't auto-sort. Must create departments WITHOUT manager_id FK, then users, then add FK via `op.create_foreign_key()`.
- **Alembic needs sys.path**: `migrations/env.py` needs `sys.path.insert(0, ...)` to find `api` package.
- **AuditLog.metadata conflict**: SQLAlchemy reserves `.metadata`. Use `extra_metadata = mapped_column("metadata", JSONB, ...)`.
- **passlib+bcrypt version**: `bcrypt>=4.1` breaks `passlib[bcrypt]`. Pin `bcrypt==4.0.1`.
- **Naive vs aware datetimes**: DB columns are `TIMESTAMP WITHOUT TIME ZONE`. Use `datetime.utcnow()` not `datetime.now(timezone.utc)` for asyncpg compatibility.
- **EmailStr needs email-validator**: Pydantic v2 `EmailStr` requires `pip install email-validator` (not in requirements.txt by default).
- **No explicit db.commit() in routes**: `get_db()` auto-commits on success. Use `await db.flush()` in routes to write to DB within the transaction. Explicit `commit()` breaks atomicity.

## Build Phase Status
- Phase 1: Scaffold + Boot **COMPLETE** (22 tables, 16 RLS, /health 200)
- Phase 2: Auth + Users **COMPLETE** (login, refresh, register, /auth/me, seed data, RBAC middleware)
- Phase 3: Core Entities CRUD **COMPLETE** (32 API paths, 9 routers: departments, users, budgets, vendors, PRs, POs, receipts, invoices, RFQs)
- Phase 4: Business Logic **COMPLETE** (34 API paths, approval chains, budget locking, audit logging, notifications)
- Phase 4 Bug Fixes **COMPLETE** (4 bugs fixed — push WouldBlock, invoice vendor_name, OCR logging, vendor onboarding email, mobile blank screen)
- **Production Hardening COMPLETE** (20 critical/high issues fixed): DEBUG=False, random vendor password, internal job auth, file tenant isolation, OCR async, rate limit X-Forwarded-For, CORS methods restricted, self-approval bypass fixed, N+1 queries fixed, all explicit db.commit() → db.flush()
- **Functional Completeness Fixes COMPLETE** (14 fixes — budget spent_cents, invoice APPROVED/PAID, PO close, RFQ cancel, exception notify, receipt triggers match, audit log route, approvals entity filter, dashboard KPIs, invoice upload UI, invoice payment buttons, approval chain on PR, mobile dispute, iOS notifications)
- **Server Latency Optimization COMPLETE** (8 fixes — NullPool→QueuePool pool_size=2, httpx singleton, rate limiter pipeline+skip /internal/, batch invoices/receipts/rfqs/approvals N+1, DB indexes migrated c9e1f2a3b4d5)
- Phase 5-9: Not started

## Post-Launch Bug Fixes (Phase 4)
- **WouldBlock**: `push_service.py` — Firebase `send_each_for_multicast` is sync; wrapped in `asyncio.run_in_executor` to avoid blocking anyio event loop
- **Invoice vendor_name**: `invoices.py` JOINs `Vendor` (outer) in list+get; `InvoiceResponse` schema has `vendor_name`; web list + detail page display it
- **OCR error recovery**: `invoice_ocr.py` outer except block now logs `ocr_failed_recovery` with error (previously silent pass)
- **Vendor onboarding email**: `vendors.py` dispatches welcome email via Brevo BackgroundTask only for new user accounts (`existing_user is None`)
- **Mobile blank screen**: `invoice_upload_screen.dart` dispatches `LoadInvoices()` before `context.pop()`; `invoice_list_screen.dart` handles `InvoiceUploaded` with spinner

## Phase 3 Bugs — FIXED in Phase 4
- RFQ vendor_id: now uses email-based vendor lookup
- Vendor bank_account_number: now saved as `bank_account_number_encrypted`
- Seed vendor user email: changed to `sales@alphasupplies.com` to match vendor record
- PR approve/reject: implemented

## RFQ Award Flow
- `POST /rfqs/{rfq_id}/award` with `{"bid_id": "..."}` — creates PO from bid, no PR required
- PO line items sourced from RFQ line items; bid.total_cents distributed by qty across lines
- RFQ status → AWARDED; PO.pr_id may be null (RFQ-sourced POs)
- Sends FCM push + email ("po_awarded" template) to winning vendor on award
- Frontend: `rfqService.award(rfqId, bidId)` → removed old `pr_id` guard
- Bug fixed: RFQ create used `"notification"` template (missing) → changed to `"rfq_issued"`

## Notification Templates (api/services/notification_service.py)
- `rfq_issued`: vendor notified when RFQ is created
- `po_issued`: vendor notified when PO is manually created
- `po_awarded`: vendor notified when RFQ bid is awarded
- `payment_approved`: vendor notified when invoice approved for payment
- `invoice_paid`: vendor notified when invoice marked as PAID
- `pr_approval_request`, `pr_approved`, `pr_rejected`, `invoice_exception`: existing

## Phase 4 Architecture Decisions
- **Budget locking**: SELECT FOR UPDATE on budget row, sum COMMITTED reservations, single atomic transaction via get_db()
- **Approval chain**: All Approval records start PENDING, lowest approval_level = current step
- **Thresholds (cents)**: <5M = manager, 5M-20M = +finance_head, >=20M = +CFO
- **Notifications**: Resolve emails during request, dispatch via BackgroundTasks (fire-and-forget)
- **No explicit db.commit()**: Let get_db() auto-commit for atomicity
- **Dashboard Stats**: Replaced multiple list API fetches with a dedicated `/api/v1/dashboard/stats` endpoint using concurrent `COUNT` and `SUM` queries mapped to a single JSON response for minimal latency.

## Seed Data (key UUIDs for testing)
- Tenant ACME: `a0000000-0000-0000-0000-000000000001`
- Eng Dept: `d0000000-...-000000000001`, Manager: eng.manager@acme.com
- Finance Head: finance.head@acme.com, CFO: cfo@acme.com
- Procurement: procurement@acme.com, Proc Lead: proc.lead@acme.com
- Budgets Q1 2026: Eng=5M, Mkt=3M, Ops=4M, Fin=2M cents
- Vendor Alpha (ACTIVE): `e0000000-...-000000000001`, email: sales@alphasupplies.com
- Password for all: `SvpmsTest123!`

## Email Service
- Changed from SendGrid (stub) to **Brevo** (active)
- `api/services/email_service.py` uses Brevo REST API via httpx
- Config: `BREVO_API_KEY` in `.env`

## Database
- Neon Postgres (eu-west-2), credentials in `.env`
- 22 tables + alembic_version
- 16 tables with RLS enabled
- Extensions: uuid-ossp, pgcrypto, pg_trgm

## Key File Locations
- Routes: `api/routes/{entity}.py` (11 files, incl. audit_logs.py)
- Models: `api/models/{entity}.py` (14 files)
- Schemas: `api/schemas/{entity}.py` (12 files, incl. audit_log.py)
- Services: `api/services/` (auth, email, firebase_push, secrets, cache, ocr, audit, budget, approval, notification)
- Middleware: `api/middleware/` (auth, tenant, authorization)
- DB: `api/database.py` (get_db with auto-commit/rollback, set_tenant_context)
- Config: `api/config.py` (Settings with extra="ignore")

## Invoice State Machine (full)
- UPLOADED → (OCR+match) → MATCHED or EXCEPTION
- EXCEPTION → DISPUTED (vendor disputes via POST /dispute)
- EXCEPTION|DISPUTED → MATCHED (finance overrides via POST /override)
- MATCHED → APPROVED (finance_head/cfo/admin via POST /approve-payment) — sets approved_payment_at
- APPROVED → PAID (finance_head/cfo/admin via POST /pay) — sets paid_at
- DB migration: `7bcdb952bddf_add_invoice_payment_fields.py` adds approved_payment_at + paid_at

## Functional Completeness Fixes Summary
- Budget: `commit_budget_spent()` called in `create_purchase_order()` after PO issued
- Receipt: triggers `run_three_way_match` as BackgroundTask for open invoices on same PO
- 3-way match: sends `invoice_exception` email to finance roles on EXCEPTION result
- Audit log: `GET /api/v1/audit-logs` with entity_type/entity_id/actor_id filters
- Approvals: `entity_type` + `entity_id` query params; privileged roles see all (not just their own)
- Mobile: `DisputeInvoice` BLoC event + dialog in invoice_detail_screen; iOS notifications fixed
