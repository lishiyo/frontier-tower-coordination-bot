from typing import AsyncGenerator
from contextlib import asynccontextmanager
import logging

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base as sa_declarative_base

from app.config import ConfigService

logger = logging.getLogger(__name__)

# Create async engine using the database URL from ConfigService
engine = create_async_engine(
    ConfigService.get_database_url(),
    echo=False,  # Set to True for SQL query logging (development only)
    future=True,  # Use SQLAlchemy 2.0 style
    pool_pre_ping=True, # Add pre-ping to check connection liveness
)

# Create async session maker
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

# Create a base class for declarative models
Base = sa_declarative_base()

POOL_RECYCLE_SECONDS = 3600  # Recycle connections every hour, e.g.

@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide a transactional scope around a series of operations."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise

async def init_db():
    async with engine.begin() as conn:
        # await conn.run_sync(Base.metadata.drop_all) # Uncomment to drop tables on startup (for dev)
        await conn.run_sync(Base.metadata.create_all)

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