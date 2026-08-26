"""Один вопрос -> SQL -> проверка -> БД -> результат. Общее ядро для ask.py и main.py.

Специально без HTTP и без print: возвращает данные, а кто их покажет —
консоль или веб — решает вызывающий код.
"""
from __future__ import annotations

import datetime as dt
import logging
import time
import uuid
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from . import db
from .llm import ask_llm
from .llm import LlmError
from .prompt import ANSWER_PROMPT, FORBIDDEN_MARKER, OFFTOPIC_MARKER, build_sql_prompt
from .roles import RolePolicy
from .sql_guard import SqlGuardError, validate_select

logger = logging.getLogger(__name__)


def _clean_value(value):
    """Приводит значение из БД к виду, пригодному для показа человеку.

    AVG() в PostgreSQL возвращает numeric с большой точностью: средний балл
    приезжает как 3.5000000000000000. Просим модель делать ROUND, но полагаться
    только на неё нельзя — она правило периодически забывает, поэтому режем
    хвост нулей и здесь.
    """
    if isinstance(value, Decimal):
        try:
            rounded = value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        except InvalidOperation:  # слишком большое число для quantize
            return float(value)
        return float(rounded)
    if isinstance(value, (dt.date, dt.time, dt.datetime)):
        return str(value)
    return value


# Сколько строк показываем модели при пересказе. Всю выборку слать нельзя —
# в критериях оценки отдельный пункт «в LLM не передаются большие массивы данных».
ROWS_FOR_SUMMARY = 20


@dataclass
class AskResult:
    question: str
    sql: str | None = None
    columns: list[str] = field(default_factory=list)
    rows: list[list] = field(default_factory=list)
    row_count: int = 0
    answer: str | None = None  # человеческий пересказ таблицы
    error: str | None = None
    error_kind: str | None = None  # refused | forbidden | db_error
    elapsed_ms: int = 0


def _table_for_summary(columns: list[str], rows: list[list], row_count: int) -> str:
    head = " | ".join(str(column) for column in columns)
    body = "\n".join(
        " | ".join("—" if value is None else str(value) for value in row)
        for row in rows[:ROWS_FOR_SUMMARY]
    )
    tail = ""
    if row_count > ROWS_FOR_SUMMARY:
        tail = f"\n… всего строк: {row_count}, показаны первые {ROWS_FOR_SUMMARY}"
    return f"{head}\n{body}{tail}"


async def _summarize(question: str, columns: list[str], rows: list[list], row_count: int) -> str:
    """Второй вызов модели: превращает таблицу в человеческую фразу."""
    if row_count == 0:
        # Пустой результат не стоит отдельного похода в сеть — фраза всегда одна.
        return "По этому запросу в базе ничего не нашлось."
    try:
        table = _table_for_summary(columns, rows, row_count)
        answer = await ask_llm(
            ANSWER_PROMPT, f"Вопрос: {question}\n\nТаблица с ответом:\n{table}", temperature=0.3
        )
        return answer.strip()
    except LlmError as exc:
        # Пересказ — украшение поверх таблицы. Если модель не ответила, показываем
        # данные без него, а не роняем весь запрос.
        logger.warning("Не удалось пересказать результат: %s", exc)
        return ""


async def answer_question(
    question: str,
    policy: RolePolicy,
    own_student_id: int | None = None,
    role: str = "unknown",
) -> AskResult:
    started = time.monotonic()
    # Свой id на запрос: при параллельной работе нескольких человек без него
    # нельзя понять, какая строка лога к какому вопросу относится.
    request_id = uuid.uuid4().hex[:12]
    logger.info("Вопрос: %s", question, extra={"event": {"request_id": request_id, "role": role}})

    system_prompt = build_sql_prompt(policy, own_student_id)
    raw_sql = (await ask_llm(system_prompt, question)).strip()
    logger.debug("Модель предложила SQL: %s", raw_sql)

    def finish(**kwargs) -> AskResult:
        result = AskResult(
            question=question,
            elapsed_ms=int((time.monotonic() - started) * 1000),
            **kwargs,
        )
        # Одна сводная запись на запрос — то, по чему потом строится аналитика.
        logger.info(
            "Запрос завершён",
            extra={
                "event": {
                    "event": "ask",
                    "request_id": request_id,
                    "role": role,
                    "student_id": own_student_id,
                    "question": question,
                    "sql": result.sql,
                    "outcome": result.error_kind or "ok",
                    "row_count": result.row_count,
                    "elapsed_ms": result.elapsed_ms,
                }
            },
        )
        return result

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
    table = [[_clean_value(row[column]) for column in columns] for row in rows]
    logger.info("Выполнено, строк: %d", len(rows))

    answer = await _summarize(question, columns, table, len(rows))

    return finish(
        sql=safe_sql,
        columns=columns,
        rows=table,
        row_count=len(rows),
        answer=answer,
    )
