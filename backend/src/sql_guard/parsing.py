"""Шаг 1: превращаем текст от модели в ровно один разобранный SQL-оператор."""
from __future__ import annotations

import sqlglot
from sqlglot import exp
from sqlglot.errors import ParseError

from .errors import SqlGuardError


def parse_single_statement(sql: str) -> exp.Expression:
    """Ничего не проверяет по смыслу — только то, что это валидный одиночный
    SQL-оператор PostgreSQL. Смысловые проверки — в остальных файлах пакета.
    """
    sql = sql.strip().rstrip(";")
    if not sql:
        raise SqlGuardError("Пустой SQL-запрос")

    try:
        statements = [s for s in sqlglot.parse(sql, dialect="postgres") if s is not None]
    except ParseError as exc:
        raise SqlGuardError(f"Не удалось разобрать SQL: {exc}") from exc

    if len(statements) != 1:
        raise SqlGuardError("Разрешён ровно один SQL-оператор за запрос (без ; в середине)")

    return statements[0]
