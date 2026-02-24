import ssl as _ssl

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    AsyncEngine,
    create_async_engine,
    async_sessionmaker,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text
from api.config import settings
import structlog

logger = structlog.get_logger()


class Base(DeclarativeBase):
    pass


def _get_db_url() -> str:
    """Strip sslmode from URL since asyncpg uses connect_args for SSL."""
    url = settings.DATABASE_URL
    url = url.replace("?sslmode=require", "").replace("&sslmode=require", "")
    return url


engine: AsyncEngine = create_async_engine(
    _get_db_url(),
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_timeout=30,
    pool_recycle=settings.DB_POOL_RECYCLE,
    pool_pre_ping=True,
    echo=settings.DEBUG,
    connect_args={"ssl": "require"},
)

AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def set_tenant_context(session: AsyncSession, tenant_id: str):
    # Use set_config() which supports parameterized queries in asyncpg,
    # eliminating the f-string interpolation risk. Third arg 'true' scopes it
    # to the current transaction only (equivalent to SET LOCAL).
    import uuid as _uuid
    _uuid.UUID(str(tenant_id))  # raises ValueError if not a valid UUID
    await session.execute(
        text("SELECT set_config('app.current_tenant_id', :tid, true)"),
        {"tid": str(tenant_id)},
    )


async def init_db():
    async with engine.begin() as conn:
        await conn.execute(text("SELECT 1"))
        logger.info("neon_db_connected")


async def close_db():
    await engine.dispose()
    logger.info("neon_db_disconnected")
