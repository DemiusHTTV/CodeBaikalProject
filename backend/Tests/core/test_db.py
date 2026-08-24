import asyncio

import pytest

from src import db


@pytest.mark.asyncio
async def test_fetch_readonly_runs_select_against_real_db():
    try:
        await asyncio.wait_for(db.init_pool(), timeout=5)
    except (OSError, asyncio.TimeoutError) as exc:
        pytest.skip(f"БД недоступна из этого окружения: {exc}")

    try:
        rows = await db.fetch_readonly("SELECT 1 AS one")
        assert rows == [{"one": 1}]
    finally:
        await db.close_pool()
