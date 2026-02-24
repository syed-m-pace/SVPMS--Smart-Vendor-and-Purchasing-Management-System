import asyncio
import httpx
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.database import AsyncSessionLocal
from sqlalchemy import select
from api.models.user import User
from api.services.auth_service import create_access_token

async def test_api():
    base_url = "https://svpms-be-gcloud-325948496969.asia-south1.run.app"
    
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(User).where(User.first_name == 'Alice', User.last_name == 'Johnson'))
        user = res.scalar_one_or_none()
        
    if not user:
        print("Alice Johnson not found.")
        return
        
    token = create_access_token(
        user_id=str(user.id),
        tenant_id=str(user.tenant_id),
        role=user.role,
        email=user.email,
        department_id=str(user.department_id) if user.department_id else None,
    )
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test endpoints
        r = await client.get(f"{base_url}/api/v1/budgets?limit=25", headers=headers)
        print(f"Status: {r.status_code}")
        print(f"Body: {r.text[:500]}")

if __name__ == "__main__":
    asyncio.run(test_api())
