"""Шаг 4: только таблицы из белого списка.

Это отсекает системные каталоги (pg_shadow, pg_authid...) и любые таблицы,
которых модель по замыслу не должна касаться.
"""
from __future__ import annotations

from sqlglot import exp

from .errors import SqlGuardError


def reject_tables_outside_whitelist(statement: exp.Expression, allowed_tables: frozenset[str]) -> None:
    # Алиасы CTE (WITH x AS (...)) — не настоящие таблицы, пропускаем их отдельно,
    # иначе любой запрос с WITH ложно отклонялся бы как обращение к "чужой" таблице.
    cte_names = {cte.alias.lower() for cte in statement.find_all(exp.CTE)}

    for table in statement.find_all(exp.Table):
        name = table.name.lower()
        if not name or (name not in allowed_tables and name not in cte_names):
            raise SqlGuardError(f"Таблица не разрешена: {table.name or '<анонимный вызов функции>'}")
