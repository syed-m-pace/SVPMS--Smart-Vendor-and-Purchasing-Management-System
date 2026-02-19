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

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise SystemExit("DATABASE_URL is required")

VENDOR_EMAIL = os.getenv("SVPMS_VENDOR_EMAIL", "")
COMMON_PASSWORD = "SvpmsTest123!"

async def fix_vendor_user():
    engine = create_async_engine(DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        if not VENDOR_EMAIL:
            raise SystemExit("SVPMS_VENDOR_EMAIL is required")

        result = await session.execute(select(Vendor).where(Vendor.email == VENDOR_EMAIL))
        vendor = result.scalar_one_or_none()
        
        if not vendor:
            print(f"Vendor {VENDOR_EMAIL} not found!")
            return

        print(f"Found Vendor: {vendor.legal_name} ({vendor.id})")

        # 2. Check if user already exists
        u_result = await session.execute(select(User).where(User.email == VENDOR_EMAIL))
        user = u_result.scalar_one_or_none()

        if user:
            print("User already exists! Resetting password...")
            user.password_hash = hash_password(COMMON_PASSWORD)
            await session.commit()
            print("Password reset.")
        else:
            print("Creating new User linked to Vendor...")
            new_user = User(
                tenant_id=vendor.tenant_id,
                email=VENDOR_EMAIL,
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
