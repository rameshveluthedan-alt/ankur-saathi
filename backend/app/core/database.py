"""
Ankur Saathi — Database Connection Pool
Uses asyncpg for async Postgres access.
Pool is created on app startup, closed on shutdown via FastAPI lifespan.
"""

import asyncpg
from contextlib import asynccontextmanager
from typing import Optional

from app.core.config import get_settings

# Module-level pool reference
_pool: Optional[asyncpg.Pool] = None


async def create_pool() -> asyncpg.Pool:
    """Create the connection pool. Called once at app startup."""
    global _pool
    settings = get_settings()
    _pool = await asyncpg.create_pool(
        settings.database_url,
        min_size=settings.db_pool_min,
        max_size=settings.db_pool_max,
    )
    return _pool


async def close_pool():
    """Close the connection pool. Called at app shutdown."""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


def get_pool() -> asyncpg.Pool:
    """Get the current pool. Raises if not initialized."""
    if _pool is None:
        raise RuntimeError("Database pool not initialized. Call create_pool() first.")
    return _pool


@asynccontextmanager
async def get_db():
    """
    Async context manager for a database connection.
    Usage:
        async with get_db() as db:
            row = await db.fetchrow("SELECT ...")
    """
    pool = get_pool()
    async with pool.acquire() as conn:
        yield conn
