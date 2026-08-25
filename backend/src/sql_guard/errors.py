"""Единственное исключение sql_guard — чтобы вызывающий код мог ловить именно его."""
from __future__ import annotations


class SqlGuardError(ValueError):
    """SQL не прошёл проверку безопасности."""
