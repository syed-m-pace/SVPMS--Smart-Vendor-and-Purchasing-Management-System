import asyncio
import os
import sys

# Ensure the project root and api module are on sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from api.models.user import User
from api.models.vendor import Vendor
from api.services.auth_service import hash_password
import uuid

# Use the production DB URL
DATABASE_URL = "postgresql+asyncpg://neondb_owner:npg_kTG3w6DYoNrZ@ep-winter-flower-abhsz7sw-pooler.eu-west-2.aws.neon.tech/neondb"

# Tenand ID for Acme (from seed)
TENANT_ID = uuid.UUID("a0000000-0000-0000-0000-000000000001")
COMMON_PASSWORD = "SvpmsTest123!"

async def fix_vendor_user():
    engine = create_async_engine(DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        # 1. Find the vendor
        # 1. Find the vendor
        vendor_email = "syedmuheeb2001@gmail.com"
        result = await session.execute(select(Vendor).where(Vendor.email == vendor_email))
        vendor = result.scalar_one_or_none()
        
        if not vendor:
            print(f"Vendor {vendor_email} not found!")
            return

        print(f"Found Vendor: {vendor.legal_name} ({vendor.id})")

        # 2. Check if user already exists
        u_result = await session.execute(select(User).where(User.email == vendor_email))
        user = u_result.scalar_one_or_none()

        if user:
            print("User already exists! Resetting password...")
            user.password_hash = hash_password(COMMON_PASSWORD)
            await session.commit()
            print("Password reset.")
        else:
            print("Creating new User linked to Vendor...")
            new_user = User(
                id=uuid.uuid4(),
                tenant_id=TENANT_ID,
                email=vendor_email,
                password_hash=hash_password(COMMON_PASSWORD),
                first_name=vendor.legal_name.split(" ")[0],
                last_name="Vendor",
                role="vendor",
                is_active=True
            )
            session.add(new_user)
            await session.commit()
            print(f"User created with ID: {new_user.id}")

if __name__ == "__main__":
    asyncio.run(fix_vendor_user())
