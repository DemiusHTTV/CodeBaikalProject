"""Консольная проверка связки роль -> вопрос -> SQL -> реальные данные, без фронта.

Запуск (из backend/):
    .venv/bin/python -m src.ask

Логика запроса живёт в pipeline.py — ровно та же, что использует HTTP API,
чтобы консоль и веб отвечали одинаково. Здесь только ввод-вывод в терминал.
"""
from __future__ import annotations

import asyncio
import logging

from . import db
from .auth import create_token, decode_token
from .config import load_database_settings
from .llm import LlmError
from .logging_config import setup_logging
from .pipeline import answer_question
from .roles import policy_for

logger = logging.getLogger(__name__)

ROLES = ("applicant", "student", "teacher", "staff")


def _choose_role() -> str:
    print(f"Роли: {', '.join(ROLES)}")
    while True:
        role = input("Выбери роль: ").strip().lower()
        if role in ROLES:
            return role
        print(f"Нет такой роли, выбери из: {', '.join(ROLES)}")


def _choose_own_student_id() -> int:
    while True:
        raw = input("Под каким student_id войти (число, см. seed.sql, напр. 1): ").strip()
        if raw.isdigit():
            return int(raw)
        print("Нужно целое число.")


def _print_table(columns: list[str], rows: list[list]) -> None:
    if not columns:
        print("(пусто)")
        return
    widths = [
        max(len(str(col)), *(len(str(row[i])) for row in rows)) if rows else len(str(col))
        for i, col in enumerate(columns)
    ]
    print(" | ".join(str(c).ljust(w) for c, w in zip(columns, widths)))
    print("-+-".join("-" * w for w in widths))
    for row in rows:
        print(" | ".join(str(v).ljust(w) for v, w in zip(row, widths)))


async def main() -> None:
    setup_logging()

    role = _choose_role()
    extra_claims = {}
    if role == "student":
        extra_claims["student_id"] = _choose_own_student_id()

    # Ровно тот же путь, что пройдёт настоящий HTTP-запрос: выпустили токен,
    # тут же его расшифровали, дальше работаем только с тем, что достали из него.
    token = create_token(role=role, subject="демо-пользователь", **extra_claims)
    payload = decode_token(token)
    policy = policy_for(payload.role)

    logger.info("Роль: %s, student_id: %s", payload.role, payload.student_id)
    print(f"\nТокен выдан для роли «{payload.role}»:\n  {token}")
    print(f"Доступные таблицы: {', '.join(sorted(policy.allowed_tables))}")
    print(f"ФИО студентов/абитуриентов: {'разрешены' if policy.allow_raw_pii else 'только агрегатно'}")
    if payload.student_id is not None:
        print(f"Свои данные: student_id = {payload.student_id}, чужие student_id запрещены")
    print()

    settings = load_database_settings()
    print(f"БД: {settings.user}@{settings.host}:{settings.port}/{settings.name}")
    await db.init_pool(settings)
    print("Готов. Пиши вопрос по-русски и жми Enter (пустая строка — выход).\n")
    try:
        while True:
            try:
                question = input("> ").strip()
            except EOFError:
                break
            if not question:
                break
            try:
                result = await answer_question(
                    question, policy, payload.student_id, role=payload.role
                )
            except LlmError as exc:
                logger.error("Модель недоступна: %s", exc)
                print(f"\n✗ Модель недоступна: {exc}\n")
                continue

            if result.error:
                print(f"\n✗ {result.error}\n")
                continue

            print(f"\nSQL:\n  {result.sql}")
            print(f"\nРезультат ({result.row_count} строк, {result.elapsed_ms} мс):")
            _print_table(result.columns, result.rows)
            print()
    finally:
        await db.close_pool()
        logger.info("Пул подключений закрыт")


if __name__ == "__main__":
    asyncio.run(main())
