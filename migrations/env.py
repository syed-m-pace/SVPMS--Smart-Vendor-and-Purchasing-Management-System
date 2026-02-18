from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool, text
from alembic import context
import os
import sys

# Add project root to sys.path so 'api' package is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load .env for DATABASE_SYNC_URL
from dotenv import load_dotenv
load_dotenv()

# Import all models so Base.metadata is populated
import api.models  # noqa: F401
from api.database import Base

config = context.config
database_url = os.getenv(
    "DATABASE_SYNC_URL", config.get_main_option("sqlalchemy.url")
)
config.set_main_option("sqlalchemy.url", database_url)
if config.config_file_name:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline():
    context.configure(
        url=database_url, target_metadata=target_metadata, literal_binds=True
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        connection.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'))
        connection.execute(text('CREATE EXTENSION IF NOT EXISTS "pgcrypto"'))
        connection.execute(text('CREATE EXTENSION IF NOT EXISTS "pg_trgm"'))
        connection.commit()
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
