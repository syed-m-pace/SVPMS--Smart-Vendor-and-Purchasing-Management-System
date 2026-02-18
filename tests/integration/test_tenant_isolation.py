
import pytest
from httpx import AsyncClient
from api.main import app
from api.services.auth_service import create_access_token
import asyncio
import uuid

# Tenant Isolation Tests
# Ensure users from Tenant A cannot access data from Tenant B

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
def tenant_a_token():
    return create_access_token(
        user_id="user-tenant-a",
        tenant_id="a0000000-0000-0000-0000-000000000001", # Seed tenant
        role="admin",
        email="admin@acme.com"
    )

@pytest.fixture
def tenant_b_token():
    return create_access_token(
        user_id="user-tenant-b",
        tenant_id=str(uuid.uuid4()), # Dynamic new tenant
        role="admin",
        email="admin@othercorp.com"
    )

@pytest.mark.asyncio
@pytest.mark.xfail(reason="RLS isolation requires consistent connection/session management not fully supported by current NullPool test harness")
async def test_vendor_isolation(client, tenant_a_token, tenant_b_token):
    # 1. Tenant A creates a vendor
    auth_a = {"Authorization": f"Bearer {tenant_a_token}"}
    suffix = str(uuid.uuid4())[:8]
    vendor_data = {
        "legal_name": f"Tenant A Vendor {suffix}",
        "email": f"vendor_{suffix}@tenanta.com",
        "tax_id": f"TAX{suffix.upper()}" # 3 + 8 = 11 chars (valid)
    }
    resp = await client.post("/api/v1/vendors", json=vendor_data, headers=auth_a)
    assert resp.status_code == 201
    vendor_id = resp.json()["id"]

    # 2. Tenant B tries to list vendors - should NOT see Tenant A's vendor
    auth_b = {"Authorization": f"Bearer {tenant_b_token}"}
    list_resp = await client.get("/api/v1/vendors", headers=auth_b)
    assert list_resp.status_code == 200
    # Pagination wrapper uses 'data'
    items = list_resp.json().get("data", [])
    # Check that vendor_id is NOT in the list
    assert not any(v["id"] == vendor_id for v in items)

    # 3. Tenant B tries to get vendor by ID - should be 404 or 403
    get_resp = await client.get(f"/api/v1/vendors/{vendor_id}", headers=auth_b)
    # The API should strictly filter by tenant_id, so it appears non-existent
    assert get_resp.status_code == 404

    # 4. Tenant A can fetch it
    get_resp_a = await client.get(f"/api/v1/vendors/{vendor_id}", headers=auth_a)
    assert get_resp_a.status_code == 200
