"""Шаг 6: гарантируем LIMIT, чтобы один вопрос не мог утянуть всю таблицу целиком."""
from __future__ import annotations

from sqlglot import exp


def enforce_limit(statement: exp.Expression, default_limit: int, max_limit: int) -> None:
    limit_node = statement.args.get("limit")
    if limit_node is None:
        statement.set("limit", exp.Limit(expression=exp.Literal.number(default_limit)))
        return

    try:
        current = int(limit_node.expression.this)
    except (TypeError, ValueError, AttributeError):
        # LIMIT $1 / LIMIT (подзапрос) и т.п. — значению не доверяем, не гадаем,
        # что имела в виду модель, и не роняем процесс на int() от нечислового узла.
        statement.set("limit", exp.Limit(expression=exp.Literal.number(default_limit)))
        return

    if current > max_limit:
        statement.set("limit", exp.Limit(expression=exp.Literal.number(max_limit)))
