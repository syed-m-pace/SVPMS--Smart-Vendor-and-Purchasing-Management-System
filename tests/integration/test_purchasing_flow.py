import pytest
from httpx import AsyncClient
from api.main import app
from api.services.auth_service import create_access_token
import asyncio

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
async def client():
    async with AsyncClient(app=app, base_url="http://test") as c:
        yield c

@pytest.fixture
def admin_token():
    return create_access_token(
        user_id="seed-admin-uuid-1234",
        tenant_id="a0000000-0000-0000-0000-000000000001",
        role="admin",
        email="admin@acme.com"
    )

@pytest.mark.asyncio
async def test_full_purchase_cycle(client, admin_token: str):
    import uuid
    # 1. Admin creates Vendor
    auth = {"Authorization": f"Bearer {admin_token}"}
    suffix = str(uuid.uuid4())[:8]
    vendor_data = {
        "legal_name": f"Test Supplier {suffix}",
        "email": f"supplier_{suffix}@test.com",
        "tax_id": f"TAX{suffix.upper()}" # 11 chars
    }
    resp = await client.post("/api/v1/vendors", json=vendor_data, headers=auth)
    if resp.status_code != 201:
        print(f"DEBUG: Create Vendor Failed: {resp.status_code} - {resp.text}")
    assert resp.status_code == 201
    vendor_id = resp.json()["id"]

    # 2. Authenticate as Procurement Lead (Assume seeded: proc.lead@acme.com)
    # Validate user exists for Audit Log FK constraints
    proc_resp = await client.post("/auth/login", json={"email": "proc.lead@acme.com", "password": "SvpmsTest123!"})
    proc_token = proc_resp.json()["access_token"]
    proc_auth = {"Authorization": f"Bearer {proc_token}"}

    # 1b. Approve Vendor (as Proc Lead) so it is ACTIVE for PO creation later
    # This triggers an audit log, so the actor (Proc Lead) must exist in users table.
    approve_resp = await client.post(f"/api/v1/vendors/{vendor_id}/approve", headers=proc_auth)
    assert approve_resp.status_code == 200
    assert approve_resp.json()["status"] == "ACTIVE"
    
    # 3. Create PR
    # Need a department_id first (get Eng dept)
    depts = await client.get("/api/v1/departments", headers=proc_auth)
    # print(f"DEBUG: Departments Response: {depts.status_code} - {depts.text}")
    assert depts.status_code == 200
    
    dept_data = depts.json()
    # Pagination response wrapper uses 'data'
    items = dept_data.get("data", [])
    if not items:
        # Fallback to 'items' if old format (some endpoints might differ)
        items = dept_data.get("items", [])
        
    if not items:
        pytest.fail(f"No departments found in seed data. Response: {dept_data}")
        
    eng_dept_id = next((d["id"] for d in items if "Eng" in d["name"]), items[0]["id"])

    # 2b. Ensure Budget exists for Engineering (as Admin)
    from datetime import datetime
    now = datetime.utcnow()
    fy = now.year
    q = (now.month - 1) // 3 + 1
    
    budget_total_cents = 1_000_000_000
    budget_data = {
        "department_id": eng_dept_id,
        "fiscal_year": fy,
        "quarter": q,
        "total_cents": budget_total_cents,
        "currency": "INR"
    }
    # Try to create budget, ignore if 409 (already exists)
    # Try to create budget, ignore if 409 (already exists)
    budget_resp = await client.post("/api/v1/budgets", json=budget_data, headers=auth)
    
    if budget_resp.status_code == 409:
         # Budget exists, we need to update it to ensure it has enough funds
         # First, find variables to query it (we know dept_id, year, quarter)
         # But the update endpoint needs budget_id.
         # So let's list budgets to find it.
         list_resp = await client.get(f"/api/v1/budgets?department_id={eng_dept_id}", headers=auth)
         assert list_resp.status_code == 200
         items = list_resp.json()["data"]
         # Find the one matching our FY/Q
         existing_budget = next((b for b in items if b["fiscal_year"] == fy and b["quarter"] == q), None)
         if existing_budget:
             b_id = existing_budget["id"]
             # Update it
             update_data = {"total_cents": budget_total_cents}
             upd_resp = await client.put(f"/api/v1/budgets/{b_id}", json=update_data, headers=auth)
             assert upd_resp.status_code == 200
    elif budget_resp.status_code != 201:
        print(f"DEBUG: Budget Creation Failed: {budget_resp.status_code} - {budget_resp.text}")

    # 2c. Authenticate as Procurement Lead
    
    pr_data = {
        "department_id": eng_dept_id,
        "description": "Urgent Hardware Upgrade",
        "line_items": [
            {
                "description": "High Performance Server",
                "quantity": 2,
                "unit_price_cents": 500000, # 5,000.00 each = 10k total
                "vendor_id": vendor_id
            }
        ]
    }
    pr_resp = await client.post("/api/v1/purchase-requests", json=pr_data, headers=proc_auth)
    assert pr_resp.status_code == 201
    pr_id = pr_resp.json()["id"]
    
    # 4. Submit PR
    submit_resp = await client.post(f"/api/v1/purchase-requests/{pr_id}/submit", headers=proc_auth)
    if submit_resp.status_code != 200:
        print(f"DEBUG: Submit PR Failed: {submit_resp.status_code} - {submit_resp.text}")
    assert submit_resp.status_code == 200
    assert submit_resp.json()["status"] == "PENDING"
    
    # 5. Manager Approves (Seed: eng.manager@acme.com)
    mgr_resp = await client.post("/auth/login", json={"email": "eng.manager@acme.com", "password": "SvpmsTest123!"})
    mgr_token = mgr_resp.json()["access_token"]
    mgr_auth = {"Authorization": f"Bearer {mgr_token}"}
    
    approve_resp = await client.post(f"/api/v1/purchase-requests/{pr_id}/approve", headers=mgr_auth, json={"comments": "Looks good"})
    assert approve_resp.status_code == 200
    assert approve_resp.json()["status"] == "APPROVED"

    # 6. Approved PR should appear in PO ready queue
    ready_resp = await client.get("/api/v1/purchase-orders/ready", headers=proc_auth)
    assert ready_resp.status_code == 200
    ready_items = ready_resp.json().get("data", [])
    assert any(item["pr_id"] == pr_id for item in ready_items)

    # 7. Verify PO Creation (Manual Step by Procurement)
    # The API does not auto-create POs on approval. Procurement must do it.
    po_data = {
        "pr_id": pr_id,
        "vendor_id": vendor_id,
        "expected_delivery_date": "2026-12-31",
        "terms_and_conditions": "Standard Terms"
    }
    po_create_resp = await client.post("/api/v1/purchase-orders", json=po_data, headers=proc_auth)
    assert po_create_resp.status_code == 201
    po_id = po_create_resp.json()["id"]
    
    # Verify PO details matches PR
    assert po_create_resp.json()["total_cents"] == pr_data["line_items"][0]["quantity"] * pr_data["line_items"][0]["unit_price_cents"]
    assert po_create_resp.json()["status"] == "ISSUED"
    assert po_create_resp.json()["issued_at"] is not None

    # 8. Once PO is created, PR should no longer be in ready queue
    ready_after_resp = await client.get("/api/v1/purchase-orders/ready", headers=proc_auth)
    assert ready_after_resp.status_code == 200
    ready_after_items = ready_after_resp.json().get("data", [])
    assert not any(item["pr_id"] == pr_id for item in ready_after_items)
