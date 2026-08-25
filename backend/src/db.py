"""Подключение к PostgreSQL и выполнение уже проверенных (sql_guard) SELECT-запросов."""
from __future__ import annotations

import asyncpg

from .config import DatabaseSettings, load_database_settings

_pool: asyncpg.Pool | None = None


async def init_pool(settings: DatabaseSettings | None = None) -> asyncpg.Pool:
    global _pool
    if _pool is None:
        settings = settings or load_database_settings()
        _pool = await asyncpg.create_pool(dsn=settings.dsn, min_size=1, max_size=10)
    return _pool


async def close_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


def get_pool() -> asyncpg.Pool:
    if _pool is None:
        raise RuntimeError("Пул подключений не инициализирован — вызовите init_pool()")
    return _pool


async def fetch_readonly(sql: str, statement_timeout_ms: int = 5000) -> list[dict]:
    """Выполняет sql в read-only транзакции с таймаутом, возвращает строки списком dict.

    read-only транзакция — вторая линия защиты после sql_guard: даже если в
    проверенном запросе как-то останется пишущая конструкция, PostgreSQL сам
    откажется её выполнить.
    """
    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction(readonly=True):
            await conn.execute(f"SET LOCAL statement_timeout = {int(statement_timeout_ms)}")
            rows = await conn.fetch(sql)
            return [dict(row) for row in rows]
