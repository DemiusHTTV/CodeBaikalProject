"""Выдача и проверка JWT — кто спрашивает, в какой роли и под каким id.

Как это устроено:
1. create_token(role, subject, ...) подписывает токен секретом JWT_SECRET из
   .env (алгоритм HS256), кладёт роль, срок годности (12 часов) и, если дали,
   student_id/teacher_id — это нужно, чтобы студент мог спросить "мои оценки",
   а guard мог проверить, что он не подсматривает данные другого student_id.
2. decode_token(token) проверяет подпись и срок годности, возвращает всё
   обратно. Если токен подделан, просрочен или подписан другим секретом —
   бросает AuthError, а не тихо доверяет содержимому.

Дальше роль и id идут в roles.py и sql_guard — этот файл сам ничего про
таблицы не знает, только про токен.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import jwt
from dotenv import load_dotenv

load_dotenv()

ALGORITHM = "HS256"
TOKEN_TTL = timedelta(hours=12)


class AuthError(RuntimeError):
    """Токен отсутствует, подделан, просрочен или подписан не тем секретом."""


@dataclass(frozen=True)
class TokenPayload:
    subject: str
    role: str
    student_id: int | None = None
    teacher_id: int | None = None


def _secret() -> str:
    return os.environ["JWT_SECRET"]


def create_token(role: str, subject: str, **extra_claims: int) -> str:
    now = datetime.now(timezone.utc)
    claims = {
        "sub": subject,
        "role": role,
        "iat": now,
        "exp": now + TOKEN_TTL,
        **extra_claims,
    }
    return jwt.encode(claims, _secret(), algorithm=ALGORITHM)


def decode_token(token: str) -> TokenPayload:
    try:
        claims = jwt.decode(token, _secret(), algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError as exc:
        raise AuthError("Токен просрочен") from exc
    except jwt.InvalidTokenError as exc:
        raise AuthError(f"Токен недействителен: {exc}") from exc

    role = claims.get("role")
    subject = claims.get("sub")
    if not role or not subject:
        raise AuthError("В токене нет роли или subject")
    return TokenPayload(
        subject=subject,
        role=role,
        student_id=claims.get("student_id"),
        teacher_id=claims.get("teacher_id"),
    )
