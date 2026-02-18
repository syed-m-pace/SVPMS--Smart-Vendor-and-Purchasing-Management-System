import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def check_users():
    url = os.environ.get("DATABASE_URL")
    if not url:
        print("DATABASE_URL not found")
        return
        
    engine = create_async_engine(url)
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT email, role FROM users"))
            users = result.all()
            if not users:
                print("No users found in database.")
            else:
                print(f"Found {len(users)} users:")
                for user in users:
                    print(f" - {user.email} ({user.role})")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(check_users())
