"""Проверка логина/пароля по служебной таблице users.

Отдельно от db.fetch_readonly: та функция рассчитана на уже провалидированный
sql_guard'ом SQL от модели и не поддерживает параметры (там их и не нужно —
LLM даёт готовую строку). Здесь наоборот — свой параметризованный запрос с
доверенным (не от модели) SQL, потому что username приходит от пользователя
и его нельзя подставлять в текст запроса напрямую.

users не входит в INTERNAL_TABLES (schema_context.py) специально не просто
так: эта таблица не должна быть видна ни модели, ни через sql_guard вообще —
только этому модулю, читающему её напрямую своим соединением.
"""
from __future__ import annotations

from dataclasses import dataclass

import bcrypt

from . import db


@dataclass(frozen=True)
class AuthenticatedUser:
    username: str
    role: str
    student_id: int | None
    teacher_id: int | None


async def verify_credentials(username: str, password: str) -> AuthenticatedUser | None:
    """Возвращает пользователя при верном логине/пароле, иначе None.

    Не различает "нет такого username" и "неверный пароль" в ответе —
    чтобы перебором логинов нельзя было выяснить, какие вообще существуют.
    """
    pool = db.get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT username, password_hash, role, student_id, teacher_id "
            "FROM users WHERE username = $1",
            username,
        )

    if row is None:
        # Всё равно тратим время на bcrypt, чтобы ответ на несуществующий
        # логин не приходил заметно быстрее, чем на неверный пароль (timing).
        bcrypt.checkpw(password.encode("utf-8"), bcrypt.hashpw(b"dummy", bcrypt.gensalt()))
        return None

    if not bcrypt.checkpw(password.encode("utf-8"), row["password_hash"].encode("utf-8")):
        return None

    return AuthenticatedUser(
        username=row["username"],
        role=row["role"],
        student_id=row["student_id"],
        teacher_id=row["teacher_id"],
    )
