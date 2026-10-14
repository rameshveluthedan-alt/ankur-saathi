"""
Ankur Saathi — Database Connection Pool
"""

import asyncpg
from contextlib import asynccontextmanager
from typing import Optional

from app.core.config import get_settings

_pool: Optional[asyncpg.Pool] = None


async def create_pool() -> asyncpg.Pool:
    global _pool
    settings = get_settings()
    _pool = await asyncpg.create_pool(
        host=settings.db_host,
        port=settings.db_port,
        user=settings.db_user,
        password=settings.db_password,
        database=settings.db_name,
        min_size=settings.db_pool_min,
        max_size=settings.db_pool_max,
        ssl=False,
    )
    return _pool


async def close_pool():
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


def get_pool() -> asyncpg.Pool:
    if _pool is None:
        raise RuntimeError("Database pool not initialized.")
    return _pool


@asynccontextmanager
async def get_db():
    pool = get_pool()
    async with pool.acquire() as conn:
        yield conn