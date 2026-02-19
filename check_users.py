import asyncio
import os
import sys

# Ensure the project root and api module are on sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from api.models.user import User
from api.models.vendor import Vendor
from api.database import Base
from sqlalchemy.orm import sessionmaker

# Use the production DB URL (or development if testing locally)
DATABASE_URL = "postgresql+asyncpg://neondb_owner:npg_kTG3w6DYoNrZ@ep-winter-flower-abhsz7sw-pooler.eu-west-2.aws.neon.tech/neondb"

async def check_users():
    engine = create_async_engine(DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        print("Checking users...")
        result = await session.execute(select(User))
        users = result.scalars().all()
        
        if not users:
            print("No users found in database!")
            return
            
        for user in users:
            print(f"User: {user.email}, Role: {user.role}, Active: {user.is_active}, Deleted: {user.deleted_at}")
            
        print("\nChecking vendors...")
        v_result = await session.execute(select(Vendor))
        vendors = v_result.scalars().all()
        for v in vendors:
            print(f"Vendor: {v.legal_name}, Email: {v.email}, Status: {v.status}")


if __name__ == "__main__":
    asyncio.run(check_users())
