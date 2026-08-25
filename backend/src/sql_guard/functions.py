"""Шаг 5: блокировка функций PostgreSQL, которые не имеют отношения к чтению данных."""
from __future__ import annotations

from sqlglot import exp

from .errors import SqlGuardError

# Доступ к файловой системе сервера, управление чужими сессиями, задержки
# (pg_sleep — способ проверить наличие уязвимости через тайминг ответа).
FORBIDDEN_FUNCTIONS = frozenset(
    {
        "pg_read_file",
        "pg_read_binary_file",
        "pg_ls_dir",
        "pg_ls_waldir",
        "lo_import",
        "lo_export",
        "pg_sleep",
        "pg_sleep_for",
        "pg_terminate_backend",
        "pg_cancel_backend",
        "dblink",
        "dblink_exec",
    }
)


def reject_forbidden_functions(statement: exp.Expression) -> None:
    for func in statement.find_all(exp.Anonymous):
        if func.name.lower() in FORBIDDEN_FUNCTIONS:
            raise SqlGuardError(f"Функция запрещена: {func.name}")
