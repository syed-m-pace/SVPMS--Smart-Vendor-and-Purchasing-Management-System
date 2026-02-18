
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

@pytest.mark.asyncio
async def test_health_check(client):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data

@pytest.mark.asyncio
async def test_public_endpoint_access(client: AsyncClient):
    # /docs should be accessible (in dev/test mode)
    response = await client.get("/docs")
    assert response.status_code == 200

@pytest.mark.asyncio
async def test_login_flow(client: AsyncClient):
    # Using seed data credentials
    login_data = {
        "email": "admin@acme.com", 
        "password": "SvpmsTest123!"
    }
    response = await client.post("/auth/login", json=login_data)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    
    # Verify token works to get /auth/me
    token = data["access_token"]
    me_response = await client.get(
        "/auth/me", 
        headers={"Authorization": f"Bearer {token}"}
    )
    assert me_response.status_code == 200
    me_data = me_response.json()
    assert me_data["email"] == "admin@acme.com"
