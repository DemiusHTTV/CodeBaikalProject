"""Шаг 6 (по роли): запрет ВЫВОДИТЬ ФИО студентов/абитуриентов не в агрегате.

Ключевая идея: смотрим на то, что запрос отдаёт наружу (список колонок после
SELECT), а не на все упоминания колонки вообще. Фильтровать по ФИО можно —
"сколько студентов на букву А" возвращает одно число и никого не раскрывает.
Выводить ФИО — нельзя.

Колонка full_name есть и у teachers/deans/staff — их ФИО показывать можно
всегда, по памятке это разрешено. Ограничены только students.full_name и
admission_applications.applicant_name — поэтому смотрим не на имя колонки
само по себе, а из какой именно таблицы оно взято.

Отдельно ловим звёздочку: SELECT * не содержит имени full_name, но при
выполнении развернётся в него — значит для таблиц с ПДн звёздочка запрещена.
"""
from __future__ import annotations

from sqlglot import exp

from .errors import SqlGuardError

# (таблица, колонка) — персональные данные конкретного студента/абитуриента.
RESTRICTED_COLUMNS = frozenset(
    {
        ("students", "full_name"),
        ("admission_applications", "applicant_name"),
    }
)
_RESTRICTED_TABLES = frozenset(table for table, _ in RESTRICTED_COLUMNS)
_RESTRICTED_COLUMN_NAMES = frozenset(column for _, column in RESTRICTED_COLUMNS)


def reject_raw_pii(statement: exp.Expression, allow_raw_pii: bool) -> None:
    if allow_raw_pii:
        return

    # alias -> реальное имя таблицы, чтобы понять, откуда взята колонка вида s.full_name
    alias_to_table = {
        table.alias_or_name.lower(): table.name.lower() for table in statement.find_all(exp.Table)
    }

    for select in statement.find_all(exp.Select):
        scope_tables = _tables_in_scope(select)
        for projection in select.expressions:
            _reject_star_over_sensitive_table(projection, alias_to_table, scope_tables)
            _reject_bare_pii_column(projection, alias_to_table, scope_tables)


def _tables_in_scope(select: exp.Select) -> frozenset[str]:
    """Таблицы, из которых этот SELECT читает напрямую (FROM + JOIN)."""
    names: set[str] = set()
    # В sqlglot 30.x ключ называется "from_", в более старых — "from".
    from_clause = select.args.get("from_") or select.args.get("from")
    if from_clause is not None:
        names.update(table.name.lower() for table in from_clause.find_all(exp.Table))
    for join in select.args.get("joins") or []:
        names.update(table.name.lower() for table in join.find_all(exp.Table))
    return frozenset(names)


def _reject_star_over_sensitive_table(
    projection: exp.Expression, alias_to_table: dict[str, str], scope_tables: frozenset[str]
) -> None:
    # SELECT * — звёздочка без указания таблицы
    if isinstance(projection, exp.Star):
        if scope_tables & _RESTRICTED_TABLES:
            raise SqlGuardError(
                "SELECT * запрещён для таблиц с персональными данными — "
                "перечисли нужные колонки явно"
            )
        return

    # SELECT s.* — звёздочка, привязанная к конкретной таблице/алиасу
    if isinstance(projection, exp.Column) and isinstance(projection.this, exp.Star):
        alias = projection.table.lower()
        real_table = alias_to_table.get(alias, alias)
        if real_table in _RESTRICTED_TABLES:
            raise SqlGuardError(
                f"{projection.table}.* запрещён — таблица содержит персональные данные, "
                "перечисли нужные колонки явно"
            )


def _reject_bare_pii_column(
    projection: exp.Expression, alias_to_table: dict[str, str], scope_tables: frozenset[str]
) -> None:
    query_touches_restricted_table = bool(scope_tables & _RESTRICTED_TABLES)

    for column in projection.find_all(exp.Column):
        name = column.name.lower()
        if name not in _RESTRICTED_COLUMN_NAMES:
            continue

        if column.table:
            real_table = alias_to_table.get(column.table.lower(), column.table.lower())
            is_restricted = (real_table, name) in RESTRICTED_COLUMNS
        else:
            # Колонку без префикса таблицы считаем риском, если в запросе вообще
            # участвует таблица с ПДн — не угадываем, к какой из таблиц JOIN она относится.
            is_restricted = query_touches_restricted_table

        if is_restricted and not _is_inside_aggregate(column, stop_at=projection):
            raise SqlGuardError(
                f"Колонка {column.name} — персональные данные студента/абитуриента, "
                "для этой роли её нельзя выводить (можно использовать в COUNT/AVG и в фильтрах)"
            )


def _is_inside_aggregate(node: exp.Expression, stop_at: exp.Expression) -> bool:
    parent = node.parent
    while parent is not None:
        if isinstance(parent, exp.AggFunc):
            return True
        if parent is stop_at:
            break
        parent = parent.parent
    return False
