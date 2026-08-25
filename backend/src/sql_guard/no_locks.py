"""Шаг 3: запрет FOR UPDATE / FOR SHARE — они блокируют строки для других запросов."""
from __future__ import annotations

from sqlglot import exp

from .errors import SqlGuardError


def reject_row_locks(statement: exp.Expression) -> None:
    # Проверяем каждый SELECT в дереве, а не только верхний — иначе блокировка
    # проходит спрятанной в подзапросе:
    #   SELECT * FROM (SELECT * FROM teachers FOR UPDATE) t
    for select in statement.find_all(exp.Select):
        if select.args.get("locks"):
            raise SqlGuardError("Блокировки строк (FOR UPDATE/FOR SHARE) запрещены")
