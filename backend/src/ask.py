"""Консольная проверка связки вопрос -> SQL -> реальные данные, без фронта.

Запуск (из backend/):
    .venv/bin/python -m src.ask

Дальше просто печатаешь вопрос по-русски и жмёшь Enter. Каждый вопрос проходит
весь путь: LLM генерирует SQL -> sql_guard проверяет -> PostgreSQL выполняет ->
на экране SQL и таблица результата. Пустая строка — выход.

Какую БД брать, решает .env (DB_HOST и т.д.) — в коде менять ничего не надо,
что для локальной БД из backend/db, что для сервера хакатона.
"""
from __future__ import annotations

import asyncio
import logging

from . import db
from .config import load_database_settings
from .llm import LlmError, ask_llm
from .logging_config import setup_logging
from .schema_context import build_schema_prompt, table_names
from .sql_guard import SqlGuardError, validate_select

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    build_schema_prompt()
    + "\n\n"
    "Ты переводишь вопрос сотрудника университета в один SQL-запрос PostgreSQL.\n"
    "Правила:\n"
    "- Верни только сам SQL-запрос: без markdown, без пояснений, без точки с запятой.\n"
    "- Разрешён только SELECT.\n"
    "- Не пиши SELECT * — перечисляй нужные колонки явно.\n"
    "- Данные студентов и абитуриентов — только агрегированно (COUNT/AVG/SUM), "
    "их ФИО никогда не выводи.\n"
)


def _print_table(rows: list[dict]) -> None:
    if not rows:
        print("(пусто)")
        return
    columns = list(rows[0].keys())
    widths = [max(len(c), *(len(str(r[c])) for r in rows)) for c in columns]
    print(" | ".join(c.ljust(w) for c, w in zip(columns, widths)))
    print("-+-".join("-" * w for w in widths))
    for row in rows:
        print(" | ".join(str(row[c]).ljust(w) for c, w in zip(columns, widths)))


async def ask_once(question: str) -> None:
    logger.info("Вопрос: %s", question)
    raw_sql = await ask_llm(SYSTEM_PROMPT, question)
    logger.debug("Модель предложила SQL: %s", raw_sql.strip())
    print(f"\nМодель предложила SQL:\n  {raw_sql.strip()}")

    try:
        safe_sql = validate_select(raw_sql, table_names())
    except SqlGuardError as exc:
        logger.warning("Запрос отклонён sql_guard: %s | исходный SQL: %s", exc, raw_sql.strip())
        print(f"\n✗ Отклонено защитой: {exc}")
        return

    logger.info("SQL прошёл проверку: %s", safe_sql)
    print(f"\nПосле проверки (с гарантированным LIMIT):\n  {safe_sql}")

    rows = await db.fetch_readonly(safe_sql)
    logger.info("Выполнено, строк: %d", len(rows))
    print(f"\nРезультат ({len(rows)} строк):")
    _print_table(rows)


async def main() -> None:
    setup_logging()
    settings = load_database_settings()
    logger.info("Подключение к БД %s@%s:%s/%s", settings.user, settings.host, settings.port, settings.name)
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
                await ask_once(question)
            except LlmError as exc:
                logger.error("Модель недоступна: %s", exc)
                print(f"\n✗ Модель недоступна: {exc}")
            print()
    finally:
        await db.close_pool()
        logger.info("Пул подключений закрыт")


if __name__ == "__main__":
    asyncio.run(main())