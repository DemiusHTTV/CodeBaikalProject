"""Какие таблицы и данные разрешены каждой роли — по памятке хакатона.

Не знает про JWT (это auth.py) и не знает про SQL (это sql_guard) — только
переводит "роль" в "что этой роли можно": список таблиц + можно ли видеть
ФИО студентов/абитуриентов не только в агрегатах.
"""
from __future__ import annotations

from dataclasses import dataclass

from .schema_context import table_names

# Таблицы, к которым не привязаны личные данные конкретного человека — общие
# справочники и институциональная статистика, видны всем ролям.
_PUBLIC_TABLES = frozenset(
    {
        "faculties",
        "departments",
        "directions",
        "groups_",
        "teachers",
        "deans",
        "staff",
        "disciplines",
        "teacher_disciplines",
        "rooms",
        "schedule",
    }
)


@dataclass(frozen=True)
class RolePolicy:
    allowed_tables: frozenset[str]
    allow_raw_pii: bool  # может ли роль видеть ФИО студентов/абитуриентов вне агрегатов


def policy_for(role: str) -> RolePolicy:
    all_tables = table_names()

    if role == "staff":
        # Деканат, бухгалтерия, ректорат — институциональный доступ целиком,
        # включая пофамильные данные студентов/абитуриентов при необходимости.
        return RolePolicy(allowed_tables=all_tables, allow_raw_pii=True)

    if role == "teacher":
        # Видит нагрузку, оценки по своим дисциплинам — но не пофамильные списки.
        return RolePolicy(
            allowed_tables=_PUBLIC_TABLES | {"students", "grades"},
            allow_raw_pii=False,
        )

    if role == "student":
        # Видит расписание, свою успеваемость (агрегатно на уровне guard) —
        # без доступа к чужим ФИО и без приёмной кампании.
        return RolePolicy(
            allowed_tables=_PUBLIC_TABLES | {"students", "grades"},
            allow_raw_pii=False,
        )

    if role == "applicant":
        # Только справочная информация о наборе — ни студентов, ни оценок.
        return RolePolicy(
            allowed_tables=_PUBLIC_TABLES | {"directions", "admission_applications"},
            allow_raw_pii=False,
        )

    raise ValueError(f"Неизвестная роль: {role!r}")
