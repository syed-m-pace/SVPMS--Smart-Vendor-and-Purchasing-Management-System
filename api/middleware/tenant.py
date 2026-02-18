from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.database import get_db, set_tenant_context
from api.middleware.auth import get_current_user


async def get_db_with_tenant(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AsyncSession:
    """FastAPI dependency: get DB session with RLS tenant context set."""
    # print(f"DEBUG: Setting tenant context to {current_user['tenant_id']}")
    await set_tenant_context(db, current_user["tenant_id"])
    return db
