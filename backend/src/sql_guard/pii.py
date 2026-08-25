"""Шаг: персональные данные нельзя выводить, даже поштучно и даже под агрегатом.

whitelist таблиц (tables.py) разрешает читать students/admission_applications —
это нужно для агрегатных отчётов (COUNT/AVG по группе, курсу и т.д.). Но сама
таблица разрешена, а не любая её колонка: ФИО студентов и абитуриентов — нельзя показывать никогда, ни в каком виде. ФИО
преподавателей/деканов/сотрудников — наоборот разрешено,конкретная колонка конкретной таблицы, а не вся таблица целиком.
"""
from __future__ import annotations

from sqlglot import exp

from .errors import SqlGuardError

# Таблица - колонки, которые нельзя выводить .
PII_COLUMNS: dict[str, frozenset[str]] = {
    "students": frozenset({"full_name"}),
    "admission_applications": frozenset({"applicant_name"}),
}


def _build_alias_map(statement: exp.Expression) -> dict[str, str]:
    """alias/имя таблицы -> реальное имя таблицы, по всему дереву запроса."""
    alias_map: dict[str, str] = {}
    for table in statement.find_all(exp.Table):
        real_name = table.name.lower()
        alias_map[table.alias_or_name.lower()] = real_name
        alias_map[real_name] = real_name
    return alias_map


def _direct_table_names(select: exp.Select) -> set[str]:
    """Таблицы, стоящие непосредственно в FROM/JOIN этого SELECT — без захода
    внутрь вложенных подзапросов/CTE (у них своя область видимости колонок).
    """
    names: set[str] = set()
    from_expr = select.args.get("from_")
    if from_expr is not None and isinstance(from_expr.this, exp.Table):
        names.add(from_expr.this.alias_or_name.lower())
    for join in select.args.get("joins") or []:
        if isinstance(join.this, exp.Table):
            names.add(join.this.alias_or_name.lower())
    return names


def reject_pii_columns(statement: exp.Expression) -> None:
    alias_map = _build_alias_map(statement)
    tables_in_statement = set(alias_map.values())
    for select in statement.find_all(exp.Select):
        direct_tables = {alias_map.get(name, name) for name in _direct_table_names(select)}
        pii_tables_here = sorted(direct_tables & PII_COLUMNS.keys())
        if pii_tables_here and any(isinstance(proj, exp.Star) for proj in select.expressions):
            raise SqlGuardError(
                "SELECT * запрещён при обращении к таблице с персональными "
                f"данными: {', '.join(pii_tables_here)}"
            )

    for column in statement.find_all(exp.Column):
        qualifier = column.table.lower() if column.table else None

        if column.name == "*":
            real_table = alias_map.get(qualifier) if qualifier else None
            if real_table in PII_COLUMNS:
                raise SqlGuardError(f"{real_table}.* запрещён — содержит персональные данные")
            continue

        col_name = column.name.lower()
        if qualifier:
            candidates = {alias_map[qualifier]} if qualifier in alias_map else set()
        else:
            candidates = tables_in_statement

        for table_name in candidates:
            if col_name in PII_COLUMNS.get(table_name, frozenset()):
                raise SqlGuardError(
                    f"Персональные данные запрещены к выводу: {table_name}.{col_name}"
                )
