import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
import uuid
from dotenv import load_dotenv

load_dotenv()

async def check_departments():
    url = os.environ.get("DATABASE_URL")
    if not url:
        print("DATABASE_URL not found")
        return
        
    engine = create_async_engine(url.replace("?sslmode=require", ""), connect_args={"ssl": "require"})
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT id, name FROM departments"))
            depts = result.all()
            print(f"Found {len(depts)} departments:")
            for d in depts:
                try:
                    uuid_obj = uuid.UUID(str(d.id))
                    print(f" - {d.name}: {d.id} (Valid UUID)")
                except ValueError:
                    print(f" - {d.name}: {d.id} (INVALID UUID)")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(check_departments())
