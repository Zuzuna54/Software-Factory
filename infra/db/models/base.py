from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.types import TypeDecorator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker
import uuid
import os

# Base class for all models
Base = declarative_base()


# Custom UUID type for SQLAlchemy
class UUID(TypeDecorator):
    """Platform-independent UUID type.
    Uses PostgreSQL's UUID type, otherwise CHAR(32)
    """

    impl = PostgresUUID
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == "postgresql":
            return str(value)
        else:
            if not isinstance(value, uuid.UUID):
                return str(uuid.UUID(value))
            else:
                return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        else:
            if not isinstance(value, uuid.UUID):
                value = uuid.UUID(value)
            return value


# Database URL configuration - to be loaded from environment variables
DATABASE_URL = os.getenv(
    "DB_CONNECTION_STRING",
    "postgresql+asyncpg://postgres:postgres@localhost/software_factory",
)
if not DATABASE_URL.startswith("postgresql+asyncpg"):
    DATABASE_URL = f"postgresql+asyncpg://{DATABASE_URL.split('://', 1)[1]}"

# Create async engine
engine = create_async_engine(DATABASE_URL)

# Create async session factory
async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


# Dependency to get DB session
async def get_db():
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()
