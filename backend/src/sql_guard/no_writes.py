"""Шаг 2: запрос не должен ничего менять — ни на верхнем уровне, ни спрятанно внутри.

sqlglot разбирает SQL в дерево (AST), а не ищет опасные слова текстом — поэтому
классическая инъекция вида `'; DROP TABLE...--` тут ни при чём: вопрос
пользователя вообще не подставляется в SQL-текст, в SQL превращается сам ответ
модели, и мы разбираем именно его структуру. Угроза здесь другая: модель может
по ошибке или под влиянием текста в вопросе сгенерировать пишущий запрос —
и вот от этого защищает данный файл.
"""
from __future__ import annotations

from sqlglot import exp

from .errors import SqlGuardError

# Любой из этих узлов означает изменение данных или схемы. Ищем их ГДЕ УГОДНО
# в дереве, а не только на верхнем уровне — иначе проходит:
#   WITH x AS (DELETE FROM grades RETURNING *) SELECT * FROM x
# — верхний оператор тут SELECT, а реальное удаление прячется внутри CTE.
_WRITE_NODE_TYPES = (
    exp.Insert,
    exp.Update,
    exp.Delete,
    exp.Drop,
    exp.Alter,
    exp.Create,
    exp.TruncateTable,
)


def reject_writes(statement: exp.Expression) -> None:
    if not isinstance(statement, (exp.Select, exp.Union)):
        raise SqlGuardError(
            f"Разрешены только SELECT-запросы, получено: {type(statement).__name__}"
        )

    if statement.args.get("into") is not None:
        raise SqlGuardError("SELECT ... INTO запрещён (создание таблиц)")

    hidden_write = next(statement.find_all(*_WRITE_NODE_TYPES), None)
    if hidden_write is not None:
        raise SqlGuardError(
            f"Изменение данных запрещено, найдено внутри запроса: {type(hidden_write).__name__}"
        )
