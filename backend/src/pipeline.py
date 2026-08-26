"""Один вопрос -> SQL -> проверка -> БД -> результат. Общее ядро для ask.py и main.py.

Специально без HTTP и без print: возвращает данные, а кто их покажет —
консоль или веб — решает вызывающий код.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

from . import db
from .llm import ask_llm
from .prompt import FORBIDDEN_MARKER, OFFTOPIC_MARKER, build_sql_prompt
from .roles import RolePolicy
from .sql_guard import SqlGuardError, validate_select

logger = logging.getLogger(__name__)


@dataclass
class AskResult:
    question: str
    sql: str | None = None
    columns: list[str] = field(default_factory=list)
    rows: list[list] = field(default_factory=list)
    row_count: int = 0
    error: str | None = None
    error_kind: str | None = None  # refused | forbidden | db_error
    elapsed_ms: int = 0


async def answer_question(
    question: str,
    policy: RolePolicy,
    own_student_id: int | None = None,
) -> AskResult:
    started = time.monotonic()
    logger.info("Вопрос: %s", question)

    system_prompt = build_sql_prompt(policy, own_student_id)
    raw_sql = (await ask_llm(system_prompt, question)).strip()
    logger.debug("Модель предложила SQL: %s", raw_sql)

    def finish(**kwargs) -> AskResult:
        return AskResult(
            question=question,
            elapsed_ms=int((time.monotonic() - started) * 1000),
            **kwargs,
        )

    # Порядок важен: FORBIDDEN проверяем первым, иначе он совпал бы с подстрокой
    # OFFTOPIC-маркера при неаккуратном ответе модели.
    if FORBIDDEN_MARKER in raw_sql:
        logger.info("Модель отказалась: данные закрыты для роли")
        return finish(
            error="На этот вопрос можно ответить только личными данными студентов "
            "или абитуриентов, а вашей роли они доступны лишь в обобщённом виде. "
            "Попробуйте спросить количество или средний показатель.",
            error_kind="forbidden",
        )

    if OFFTOPIC_MARKER in raw_sql:
        logger.info("Модель отказалась: вопрос не про базу")
        return finish(
            error="Я отвечаю только на вопросы по данным университета — "
            "факультеты, группы, нагрузка, успеваемость, приёмная кампания.",
            error_kind="refused",
        )

    try:
        safe_sql = validate_select(
            raw_sql,
            policy.allowed_tables,
            allow_raw_pii=policy.allow_raw_pii,
            own_student_id=own_student_id,
        )
    except SqlGuardError as exc:
        logger.warning("Запрос отклонён sql_guard: %s | исходный SQL: %s", exc, raw_sql)
        return finish(error=str(exc), error_kind="forbidden")

    logger.info("SQL прошёл проверку: %s", safe_sql)
    try:
        rows = await db.fetch_readonly(safe_sql)
    except Exception as exc:
        logger.exception("Ошибка выполнения SQL")
        return finish(sql=safe_sql, error=f"Ошибка выполнения запроса: {exc}", error_kind="db_error")

    columns = list(rows[0].keys()) if rows else []
    logger.info("Выполнено, строк: %d", len(rows))
    return finish(
        sql=safe_sql,
        columns=columns,
        rows=[[row[column] for column in columns] for row in rows],
        row_count=len(rows),
    )
