from __future__ import annotations

import sqlglot
from sqlglot import exp
from sqlglot.errors import ParseError

DEFAULT_LIMIT = 200
MAX_LIMIT = 1000

# Функции, которые не должны встречаться в LLM-генерируемых запросах ни при каких
# обстоятельствах: доступ к файловой системе/серверу, управление сессиями, задержки.
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


class SqlGuardError(ValueError):
    """SQL не прошёл проверку безопасности."""


def validate_select(
    sql: str,
    allowed_tables: frozenset[str],
    default_limit: int = DEFAULT_LIMIT,
    max_limit: int = MAX_LIMIT,
) -> str:
    """Проверяет, что sql — безопасный одиночный SELECT по разрешённым таблицам,
    и возвращает готовую к выполнению строку с гарантированным LIMIT.
    Бросает SqlGuardError на любое нарушение.
    """
    sql = sql.strip().rstrip(";")
    if not sql:
        raise SqlGuardError("Пустой SQL-запрос")

    try:
        statements = [s for s in sqlglot.parse(sql, dialect="postgres") if s is not None]
    except ParseError as exc:
        raise SqlGuardError(f"Не удалось разобрать SQL: {exc}") from exc

    if len(statements) != 1:
        raise SqlGuardError("Разрешён ровно один SQL-оператор за запрос")

    statement = statements[0]
    if not isinstance(statement, (exp.Select, exp.Union)):
        raise SqlGuardError(f"Разрешены только SELECT-запросы, получено: {type(statement).__name__}")

    if statement.args.get("into") is not None:
        raise SqlGuardError("SELECT ... INTO запрещён (создание таблиц)")

    if statement.args.get("locks"):
        raise SqlGuardError("Блокировки строк (FOR UPDATE/FOR SHARE) запрещены")

    cte_names = {cte.alias.lower() for cte in statement.find_all(exp.CTE)}

    for table in statement.find_all(exp.Table):
        name = table.name.lower()
        if not name or (name not in allowed_tables and name not in cte_names):
            raise SqlGuardError(f"Таблица не разрешена: {table.name or '<анонимный вызов функции>'}")

    for func in statement.find_all(exp.Anonymous):
        if func.name.lower() in FORBIDDEN_FUNCTIONS:
            raise SqlGuardError(f"Функция запрещена: {func.name}")

    limit_node = statement.args.get("limit")
    if limit_node is None:
        statement.set("limit", exp.Limit(expression=exp.Literal.number(default_limit)))
    else:
        current = int(limit_node.expression.this)
        if current > max_limit:
            statement.set("limit", exp.Limit(expression=exp.Literal.number(max_limit)))

    return statement.sql(dialect="postgres")
