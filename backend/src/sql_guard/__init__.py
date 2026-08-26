"""Проверка SQL, который сгенерировала модель, перед выполнением на реальной БД.

validate_select() ничего не делает сам — он по очереди зовёт проверки из
соседних файлов, каждый отвечает ровно за одну вещь:

  parsing.py    — это вообще один валидный SQL-оператор?
  no_writes.py  — он точно ничего не меняет (ни явно, ни спрятанно в CTE)?
  no_locks.py   — он не блокирует строки (FOR UPDATE/FOR SHARE)?
  tables.py     — он не лезет в таблицы вне белого списка?
  functions.py  — он не вызывает опасные функции PostgreSQL?
  no_raw_pii.py — он не выводит ФИО студента/абитуриента не в агрегате (по роли)?
  own_rows.py   — если роль привязана к student_id, не лезет ли он к чужому?
  limits.py     — на выходе гарантированно есть разумный LIMIT?

Любой шаг может отклонить запрос через SqlGuardError — единственное исключение,
которое стоит ловить вызывающему коду.
"""
from __future__ import annotations

import logging

from .errors import SqlGuardError
from .functions import reject_forbidden_functions
from .limits import enforce_limit
from .no_locks import reject_row_locks
from .no_raw_pii import reject_raw_pii
from .no_writes import reject_writes
from .own_rows import reject_other_students_rows
from .parsing import parse_single_statement
from .tables import reject_tables_outside_whitelist

logger = logging.getLogger(__name__)

DEFAULT_LIMIT = 200
MAX_LIMIT = 1000

__all__ = ["SqlGuardError", "DEFAULT_LIMIT", "MAX_LIMIT", "validate_select"]


def validate_select(
    sql: str,
    allowed_tables: frozenset[str],
    default_limit: int = DEFAULT_LIMIT,
    max_limit: int = MAX_LIMIT,
    allow_raw_pii: bool = False,
    own_student_id: int | None = None,
) -> str:
    """Проверяет sql по всем шагам выше и возвращает готовую к выполнению строку
    с гарантированным LIMIT. Бросает SqlGuardError на первое найденное нарушение.

    allow_raw_pii по умолчанию запрещает: секьюрно по умолчанию, а не наоборот —
    роль должна явно получить разрешение (см. roles.py), а не полагаться на то,
    что вызывающий код не забыл его отключить. own_student_id задаётся только
    для роли student — тогда запрос не может фильтровать чужой student_id.
    """
    try:
        statement = parse_single_statement(sql)
        reject_writes(statement)
        reject_row_locks(statement)
        reject_tables_outside_whitelist(statement, allowed_tables)
        reject_forbidden_functions(statement)
        reject_raw_pii(statement, allow_raw_pii)
        reject_other_students_rows(statement, own_student_id)
        enforce_limit(statement, default_limit, max_limit)
    except SqlGuardError as exc:
        logger.warning("sql_guard отклонил запрос: %s | sql=%r", exc, sql)
        raise
    return statement.sql(dialect="postgres")
