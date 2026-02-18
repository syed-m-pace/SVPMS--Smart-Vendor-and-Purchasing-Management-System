
import asyncio
from sqlalchemy import text
from api.database import engine

async def force_rls():
    async with engine.begin() as conn:
        await conn.execute(text("ALTER TABLE vendors FORCE ROW LEVEL SECURITY"))
        print("RLS forced on vendors table.")

if __name__ == "__main__":
    asyncio.run(force_rls())
