from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base

from app.config import ConfigService

# Create async engine using the database URL from ConfigService
engine = create_async_engine(
    ConfigService.get_database_url(),
    echo=False,  # Set to True for SQL query logging (development only)
    future=True,  # Use SQLAlchemy 2.0 style
)

# Create async session maker
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

# Create a base class for declarative models
Base = declarative_base()

# Dependency for FastAPI (if needed later)
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency function that yields a SQLAlchemy async session.
    To be used with FastAPI dependency injection if needed later.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close() 