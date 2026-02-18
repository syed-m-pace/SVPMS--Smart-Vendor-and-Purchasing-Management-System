
import asyncio
import os
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from api.main import app
from api.database import Base, get_db
from api.config import settings
from api.services.auth_service import create_access_token

@pytest.fixture
def admin_token():
    # Helper to generate a token for admin@acme.com
    return create_access_token(
        user_id="seed-admin-uuid-1234", # Mock ID
        tenant_id="a0000000-0000-0000-0000-000000000001",
        role="admin",
        email="admin@acme.com"
    )

@pytest.fixture
def auth_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}
