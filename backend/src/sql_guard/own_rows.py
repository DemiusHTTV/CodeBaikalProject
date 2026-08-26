"""Шаг 8 (для роли student): нельзя фильтровать чужой student_id.

Отдельно от no_raw_pii.py — там про ФИО, тут про то, что студент не должен
подсматривать данные (оценки, задолженности) КОНКРЕТНОГО другого студента
по его id, даже без имени. own_student_id = None означает "роль не привязана
к одному человеку" (staff/teacher/applicant) — тогда проверка не действует.

Обычный JOIN вида "grades.student_id = students.student_id" не трогаем —
это сравнение колонка-с-колонкой, а не поиск конкретного чужого id.
"""
from __future__ import annotations

from sqlglot import exp

from .errors import SqlGuardError

_ID_COLUMN = "student_id"


def reject_other_students_rows(statement: exp.Expression, own_student_id: int | None) -> None:
    if own_student_id is None:
        return

    for node in statement.find_all(exp.EQ):
        literal = _literal_compared_to_id_column(node.this, node.expression)
        if literal is not None:
            _check(literal, own_student_id)

    for node in statement.find_all(exp.In):
        if isinstance(node.this, exp.Column) and node.this.name.lower() == _ID_COLUMN:
            for value in node.expressions:
                if isinstance(value, exp.Literal):
                    _check(value, own_student_id)


def _literal_compared_to_id_column(left: exp.Expression, right: exp.Expression) -> exp.Literal | None:
    if isinstance(left, exp.Column) and left.name.lower() == _ID_COLUMN and isinstance(right, exp.Literal):
        return right
    if isinstance(right, exp.Column) and right.name.lower() == _ID_COLUMN and isinstance(left, exp.Literal):
        return left
    return None


def _check(literal: exp.Literal, own_student_id: int) -> None:
    try:
        value = int(literal.this)
    except (TypeError, ValueError):
        raise SqlGuardError("Не удалось проверить student_id в запросе — значение не число") from None

    if value != own_student_id:
        raise SqlGuardError(
            f"Роль ограничена собственными данными (student_id={own_student_id}), "
            f"запрос обращается к student_id={value}"
        )
