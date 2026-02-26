import asyncio
from sqlalchemy import select, insert, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import uuid
import os
import sys

# Setup environment access
from api.config import settings
from api.models.contract import Contract, ContractVendor

# Create async engine directly to isolate from app lifecycle constraints
url = settings.DATABASE_URL.replace("?sslmode=require", "").replace("&sslmode=require", "")
engine = create_async_engine(url, connect_args={"ssl": "require"})
AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

async def run_migration():
    async with AsyncSessionLocal() as session:
        try:
            print("Finding existing contracts with strict vendor mappings...")
            result = await session.execute(
                select(Contract).where(Contract.vendor_id.isnot(None))
            )
            contracts = result.scalars().all()
            if not contracts:
                 print("No migrations needed.")
                 return

            print(f"Found {len(contracts)} contracts to migrate.")
            
            migrated = 0
            for c in contracts:
                # check if map already exists
                cv_result = await session.execute(
                    select(ContractVendor).where(
                        ContractVendor.contract_id == c.id,
                        ContractVendor.vendor_id == c.vendor_id
                    )
                )
                if not cv_result.scalar_one_or_none():
                    cv = ContractVendor(
                        id=uuid.uuid4(),
                        tenant_id=c.tenant_id,
                        contract_id=c.id,
                        vendor_id=c.vendor_id,
                        status=c.status,
                    )
                    session.add(cv)
                    migrated += 1
            
            await session.commit()
            print(f"Successfully migrated {migrated} mappings into contract_vendors.")
        except Exception as e:
            await session.rollback()
            print(f"Migration Failed: {str(e)}")
        finally:
            await session.close()
            await engine.dispose()

if __name__ == "__main__":
    asyncio.run(run_migration())
