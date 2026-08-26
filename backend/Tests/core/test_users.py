import asyncio

import pytest

from src import db
from src.users import verify_credentials


async def _connect_or_skip() -> None:
    try:
        await asyncio.wait_for(db.init_pool(), timeout=5)
    except (OSError, asyncio.TimeoutError) as exc:
        pytest.skip(f"БД недоступна из этого окружения: {exc}")


@pytest.mark.asyncio
async def test_verify_credentials_accepts_correct_password():
    await _connect_or_skip()
    try:
        user = await verify_credentials("student1", "student12345")
        assert user is not None
        assert user.role == "student"
        assert user.student_id == 1
        assert user.teacher_id is None
    finally:
        await db.close_pool()


@pytest.mark.asyncio
async def test_verify_credentials_rejects_wrong_password():
    await _connect_or_skip()
    try:
        assert await verify_credentials("student1", "не тот пароль") is None
    finally:
        await db.close_pool()


@pytest.mark.asyncio
async def test_verify_credentials_rejects_unknown_username():
    await _connect_or_skip()
    try:
        assert await verify_credentials("нет-такого-юзера", "любой пароль") is None
    finally:
        await db.close_pool()


@pytest.mark.asyncio
async def test_verify_credentials_binds_teacher_to_teacher_id():
    await _connect_or_skip()
    try:
        user = await verify_credentials("teacher1", "teacher12345")
        assert user is not None
        assert user.role == "teacher"
        assert user.teacher_id == 1
        assert user.student_id is None
    finally:
        await db.close_pool()


@pytest.mark.asyncio
async def test_verify_credentials_for_staff():
    await _connect_or_skip()
    try:
        user = await verify_credentials("staff1", "staff12345")
        assert user is not None
        assert user.role == "staff"
    finally:
        await db.close_pool()
