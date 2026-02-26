import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from config import settings

async def run():
    print("Starting raw SQL data migration for Contracts...")
    url = settings.DATABASE_URL.replace("?sslmode=require", "").replace("&sslmode=require", "")
    engine = create_async_engine(url, connect_args={"ssl": "require"})
    async with engine.begin() as conn:
        query = text("""
            INSERT INTO contract_vendors (id, tenant_id, contract_id, vendor_id, status, assigned_at)
            SELECT gen_random_uuid(), tenant_id, id, vendor_id, status, NOW()
            FROM contracts
            WHERE vendor_id IS NOT NULL
            ON CONFLICT DO NOTHING;
        """)
        result = await conn.execute(query)
        print(f"Migrated row count: {result.rowcount}")
    
    await engine.dispose()
    print("Migration complete.")

if __name__ == "__main__":
    asyncio.run(run())
