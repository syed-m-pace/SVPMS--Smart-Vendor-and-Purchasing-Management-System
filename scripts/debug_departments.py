import asyncio
import os
import sys

# Add project root to path
sys.path.append(os.getcwd())

from api.database import AsyncSessionLocal, set_tenant_context
from sqlalchemy import select
from api.models import Department

async def main():
    async with AsyncSessionLocal() as db:
        # Authenticate as seeded tenant
        await set_tenant_context(db, 'a0000000-0000-0000-0000-000000000001')
        
        result = await db.execute(select(Department))
        departments = result.scalars().all()
        
        print(f"Total Departments: {len(departments)}")
        print("-" * 60)
        print(f"{'ID':<40} | {'Name'}")
        print("-" * 60)
        for d in departments:
            print(f"{str(d.id):<40} | {d.name}")

if __name__ == "__main__":
    asyncio.run(main())
