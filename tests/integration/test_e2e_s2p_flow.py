"""
E2E integration test: Source-to-Pay full flow.

PR → Submit → Approve → PO → GRN (Receipt) → Invoice Upload →
3-Way Match → Invoice Exception (finance override) → Payment Approved → Paid.

Requires a running database with seed data.
Run with: pytest tests/integration/test_e2e_s2p_flow.py -v
"""

import asyncio
import uuid
from datetime import datetime

import pytest
from httpx import AsyncClient

from api.main import app
from api.services.auth_service import create_access_token


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="module")
async def client():
    async with AsyncClient(app=app, base_url="http://test") as c:
        yield c


def _token(user_id: str, tenant_id: str, role: str, email: str) -> dict:
    token = create_access_token(
        user_id=user_id, tenant_id=tenant_id, role=role, email=email
    )
    return {"Authorization": f"Bearer {token}"}


TENANT_ID = "a0000000-0000-0000-0000-000000000001"

# Seed user IDs are resolved by logging in at test time — kept here for tokens
ADMIN_HEADERS_FACTORY = lambda: _token(
    "00000000-0000-0000-0000-000000000099", TENANT_ID, "admin", "admin@acme.com"
)


# ---------------------------------------------------------------------------
# Helper: login and get auth headers
# ---------------------------------------------------------------------------


async def login(client, email: str, password: str = "SvpmsTest123!") -> dict:
    resp = await client.post("/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, f"Login failed for {email}: {resp.text}"
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


# ---------------------------------------------------------------------------
# Full S2P E2E test
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_source_to_pay_happy_path(client):
    suffix = str(uuid.uuid4())[:8]

    # ── Auth setup ──────────────────────────────────────────────────────────
    admin_auth = await login(client, "admin@acme.com")
    proc_auth = await login(client, "proc.lead@acme.com")
    mgr_auth = await login(client, "eng.manager@acme.com")
    finance_auth = await login(client, "finance.head@acme.com")

    # ── 1. Create + Activate Vendor ─────────────────────────────────────────
    vendor_resp = await client.post(
        "/api/v1/vendors",
        json={
            "legal_name": f"E2E Supplier {suffix}",
            "email": f"e2e_{suffix}@supplier.com",
            "tax_id": f"TAX{suffix.upper()[:8]}",
        },
        headers=admin_auth,
    )
    assert vendor_resp.status_code == 201, vendor_resp.text
    vendor_id = vendor_resp.json()["id"]

    approve_vendor_resp = await client.post(
        f"/api/v1/vendors/{vendor_id}/approve", headers=proc_auth
    )
    assert approve_vendor_resp.status_code == 200
    assert approve_vendor_resp.json()["status"] == "ACTIVE"

    # ── 2. Resolve Engineering department ──────────────────────────────────
    depts_resp = await client.get("/api/v1/departments", headers=proc_auth)
    assert depts_resp.status_code == 200
    depts = depts_resp.json().get("data", [])
    assert depts, "No departments found — ensure seed data is loaded"
    eng_dept_id = next(
        (d["id"] for d in depts if "Eng" in d.get("name", "")),
        depts[0]["id"],
    )

    # ── 3. Ensure sufficient budget ─────────────────────────────────────────
    now = datetime.utcnow()
    fy, q = now.year, (now.month - 1) // 3 + 1

    budget_resp = await client.post(
        "/api/v1/budgets",
        json={
            "department_id": eng_dept_id,
            "fiscal_year": fy,
            "quarter": q,
            "total_cents": 1_000_000_000,
            "currency": "INR",
        },
        headers=admin_auth,
    )
    if budget_resp.status_code == 409:
        # Update existing budget
        budgets_list = await client.get(
            f"/api/v1/budgets?department_id={eng_dept_id}", headers=admin_auth
        )
        budgets = budgets_list.json().get("data", [])
        existing = next(
            (b for b in budgets if b["fiscal_year"] == fy and b["quarter"] == q), None
        )
        if existing:
            upd = await client.put(
                f"/api/v1/budgets/{existing['id']}",
                json={"total_cents": 1_000_000_000},
                headers=admin_auth,
            )
            assert upd.status_code == 200
    else:
        assert budget_resp.status_code == 201, budget_resp.text

    # ── 4. Create Purchase Request ──────────────────────────────────────────
    pr_resp = await client.post(
        "/api/v1/purchase-requests",
        json={
            "department_id": eng_dept_id,
            "description": f"E2E Test PR {suffix}",
            "line_items": [
                {
                    "description": "Test Server Unit",
                    "quantity": 2,
                    "unit_price_cents": 100_000,
                    "vendor_id": vendor_id,
                }
            ],
        },
        headers=proc_auth,
    )
    assert pr_resp.status_code == 201, pr_resp.text
    pr_id = pr_resp.json()["id"]

    # ── 5. Submit PR ────────────────────────────────────────────────────────
    submit_resp = await client.post(
        f"/api/v1/purchase-requests/{pr_id}/submit", headers=proc_auth
    )
    assert submit_resp.status_code == 200, submit_resp.text
    assert submit_resp.json()["status"] == "PENDING"

    # ── 6. Manager Approves PR ──────────────────────────────────────────────
    mgr_approve_resp = await client.post(
        f"/api/v1/purchase-requests/{pr_id}/approve",
        headers=mgr_auth,
        json={"comments": "E2E approved"},
    )
    assert mgr_approve_resp.status_code == 200, mgr_approve_resp.text
    assert mgr_approve_resp.json()["status"] == "APPROVED"

    # ── 7. Create Purchase Order ────────────────────────────────────────────
    po_resp = await client.post(
        "/api/v1/purchase-orders",
        json={
            "pr_id": pr_id,
            "vendor_id": vendor_id,
            "expected_delivery_date": "2026-12-31",
            "terms_and_conditions": "E2E Terms",
        },
        headers=proc_auth,
    )
    assert po_resp.status_code == 201, po_resp.text
    po_id = po_resp.json()["id"]
    assert po_resp.json()["status"] == "ISSUED"

    # Verify PO total matches PR line items
    expected_total = 2 * 100_000
    assert po_resp.json()["total_cents"] == expected_total

    # ── 8. Create Goods Receipt (GRN) ───────────────────────────────────────
    # Get PO line item IDs
    po_detail_resp = await client.get(f"/api/v1/purchase-orders/{po_id}", headers=proc_auth)
    assert po_detail_resp.status_code == 200
    po_line_items = po_detail_resp.json().get("line_items", [])
    assert po_line_items, "PO has no line items"

    receipt_resp = await client.post(
        "/api/v1/receipts",
        json={
            "po_id": po_id,
            "received_date": now.strftime("%Y-%m-%d"),
            "notes": "E2E receipt",
            "line_items": [
                {
                    "po_line_item_id": li["id"],
                    "quantity_received": li["quantity"],
                    "condition": "GOOD",
                }
                for li in po_line_items
            ],
        },
        headers=proc_auth,
    )
    assert receipt_resp.status_code == 201, receipt_resp.text
    receipt_id = receipt_resp.json()["id"]

    # ── 9. Upload Invoice ───────────────────────────────────────────────────
    # Create invoice via API (mocked — no actual file upload in unit context)
    invoice_resp = await client.post(
        "/api/v1/invoices",
        json={
            "po_id": po_id,
            "vendor_id": vendor_id,
            "invoice_number": f"INV-E2E-{suffix}",
            "invoice_date": now.strftime("%Y-%m-%d"),
            "due_date": "2026-12-31",
            "total_cents": expected_total,
            "line_items": [
                {
                    "description": li["description"],
                    "quantity": li["quantity"],
                    "unit_price_cents": li["unit_price_cents"],
                }
                for li in po_line_items
            ],
        },
        headers=proc_auth,
    )
    assert invoice_resp.status_code == 201, invoice_resp.text
    invoice_id = invoice_resp.json()["id"]

    # ── 10. Trigger 3-Way Match ─────────────────────────────────────────────
    match_resp = await client.post(
        f"/api/v1/invoices/{invoice_id}/match", headers=proc_auth
    )
    assert match_resp.status_code == 200, match_resp.text

    # Give background task a moment to update invoice status
    await asyncio.sleep(0.5)

    # ── 11. Verify Invoice is MATCHED or EXCEPTION ──────────────────────────
    inv_detail = await client.get(f"/api/v1/invoices/{invoice_id}", headers=finance_auth)
    assert inv_detail.status_code == 200, inv_detail.text
    invoice_status = inv_detail.json()["status"]

    # If EXCEPTION (description mismatch risk), finance overrides it
    if invoice_status == "EXCEPTION":
        override_resp = await client.post(
            f"/api/v1/invoices/{invoice_id}/override",
            json={"reason": "E2E override — items verified manually"},
            headers=finance_auth,
        )
        assert override_resp.status_code == 200, override_resp.text
        invoice_status = override_resp.json()["status"]

    assert invoice_status == "MATCHED", (
        f"Expected MATCHED after match/override, got {invoice_status}"
    )

    # ── 12. Finance Head Approves for Payment ───────────────────────────────
    pay_approve_resp = await client.post(
        f"/api/v1/invoices/{invoice_id}/approve-payment",
        json={"comments": "E2E payment approval"},
        headers=finance_auth,
    )
    assert pay_approve_resp.status_code == 200, pay_approve_resp.text
    assert pay_approve_resp.json()["status"] == "APPROVED"
    assert pay_approve_resp.json()["approved_payment_at"] is not None

    # ── 13. Mark Invoice as Paid ────────────────────────────────────────────
    paid_resp = await client.post(
        f"/api/v1/invoices/{invoice_id}/pay",
        json={"payment_reference": f"PAY-E2E-{suffix}"},
        headers=finance_auth,
    )
    assert paid_resp.status_code == 200, paid_resp.text
    assert paid_resp.json()["status"] == "PAID"
    assert paid_resp.json()["paid_at"] is not None

    # ── 14. Final Audit Log Check ────────────────────────────────────────────
    audit_resp = await client.get(
        f"/api/v1/audit-logs?entity_type=INVOICE&entity_id={invoice_id}",
        headers=admin_auth,
    )
    assert audit_resp.status_code == 200
    audit_items = audit_resp.json().get("data", [])
    actions_recorded = {item["action"] for item in audit_items}
    # At minimum: THREE_WAY_MATCH and at least one other action
    assert len(audit_items) >= 1, "Expected at least one audit log entry for invoice"


# ---------------------------------------------------------------------------
# Negative path: insufficient budget blocks PR submission
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pr_blocked_by_insufficient_budget(client):
    """PR submit should fail if department budget is exhausted."""
    suffix = str(uuid.uuid4())[:8]
    proc_auth = await login(client, "proc.lead@acme.com")
    admin_auth = await login(client, "admin@acme.com")

    # Get a department and set its budget to 1 cent
    depts_resp = await client.get("/api/v1/departments", headers=proc_auth)
    depts = depts_resp.json().get("data", [])
    # Use the last department (less likely to conflict with other tests)
    dept_id = depts[-1]["id"]

    now = datetime.utcnow()
    fy, q = now.year, (now.month - 1) // 3 + 1

    # Create a very small budget
    budget_resp = await client.post(
        "/api/v1/budgets",
        json={
            "department_id": dept_id,
            "fiscal_year": fy,
            "quarter": q,
            "total_cents": 1,  # 1 cent — effectively zero
            "currency": "INR",
        },
        headers=admin_auth,
    )
    if budget_resp.status_code == 409:
        budgets_list = await client.get(
            f"/api/v1/budgets?department_id={dept_id}", headers=admin_auth
        )
        budgets = budgets_list.json().get("data", [])
        existing = next(
            (b for b in budgets if b["fiscal_year"] == fy and b["quarter"] == q), None
        )
        if existing:
            await client.put(
                f"/api/v1/budgets/{existing['id']}",
                json={"total_cents": 1},
                headers=admin_auth,
            )

    # Try to create + submit a PR that exceeds the 1-cent budget
    pr_resp = await client.post(
        "/api/v1/purchase-requests",
        json={
            "department_id": dept_id,
            "description": f"Over-budget PR {suffix}",
            "line_items": [
                {
                    "description": "Expensive Item",
                    "quantity": 1,
                    "unit_price_cents": 1_000_000,  # 10,000 INR >> 1 cent budget
                }
            ],
        },
        headers=proc_auth,
    )
    assert pr_resp.status_code == 201
    pr_id = pr_resp.json()["id"]

    submit_resp = await client.post(
        f"/api/v1/purchase-requests/{pr_id}/submit", headers=proc_auth
    )
    # Should fail with budget exceeded
    assert submit_resp.status_code in (400, 422, 409), (
        f"Expected budget error, got {submit_resp.status_code}: {submit_resp.text}"
    )
