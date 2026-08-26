"""Схема БД: список таблиц/колонок для sql_guard и текстовое описание для промпта LLM."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import sqlglot
from sqlglot import exp

SCHEMA_SQL_PATH = Path(__file__).resolve().parent.parent / "db" / "schema.sql"

# Таблицы с персональными данными — по памятке хакатона такие данные можно
# выводить только в агрегированном/обезличенном виде, не пофамильно.
SENSITIVE_TABLES = frozenset({"students", "admission_applications", "grades"})

# Служебные таблицы (авторизация и т.п.) — не часть предметной области вуза.
# Не должны попадать ни в промпт модели, ни в whitelist sql_guard: иначе через
# обычный вопрос можно было бы выгрузить password_hash из users.
INTERNAL_TABLES = frozenset({"users"})


@dataclass(frozen=True)
class ColumnInfo:
    name: str
    type: str


@dataclass(frozen=True)
class TableInfo:
    name: str
    columns: tuple[ColumnInfo, ...]
    sensitive: bool


def _load_schema_sql(path: Path = SCHEMA_SQL_PATH) -> str:
    return path.read_text(encoding="utf-8")


def parse_tables(schema_sql: str | None = None) -> list[TableInfo]:
    sql = schema_sql if schema_sql is not None else _load_schema_sql()
    tables: list[TableInfo] = []
    for statement in sqlglot.parse(sql, dialect="postgres"):
        if not isinstance(statement, exp.Create) or statement.kind != "TABLE":
            continue
        schema_expr = statement.this
        table_name = schema_expr.this.this.this
        if table_name in INTERNAL_TABLES:
            continue
        columns = tuple(
            ColumnInfo(name=col.this.this, type=col.kind.sql(dialect="postgres"))
            for col in schema_expr.expressions
            if isinstance(col, exp.ColumnDef)
        )
        tables.append(TableInfo(name=table_name, columns=columns, sensitive=table_name in SENSITIVE_TABLES))
    return tables


def table_names(tables: list[TableInfo] | None = None) -> frozenset[str]:
    return frozenset(table.name for table in (tables if tables is not None else parse_tables()))


def build_schema_prompt(tables: list[TableInfo] | None = None) -> str:
    """Текстовое описание схемы для промпта LLM: таблицы, колонки, пометки о ПДн."""
    tables = tables if tables is not None else parse_tables()
    lines = ["Схема базы данных PostgreSQL. Разрешены только SELECT-запросы.", ""]
    for table in tables:
        columns = ", ".join(f"{col.name} {col.type}" for col in table.columns)
        note = " -- содержит персональные данные, выводить только агрегированно/обезличенно" if table.sensitive else ""
        lines.append(f"- {table.name}({columns}){note}")
    return "\n".join(lines)
