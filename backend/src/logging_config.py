"""Единая настройка логирования для всего проекта.

Вызывается один раз при старте (см. src/ask.py). Все остальные модули
просто делают logging.getLogger(__name__) и ничего не настраивают сами.
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path

LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
LOG_FILE = LOG_DIR / "app.log"


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "time": self.formatTime(record, "%Y-%m-%d %H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        # Поля, переданные через logger.info(..., extra={"event": {...}}), кладём
        # в JSON отдельными ключами — иначе по логу нельзя ничего посчитать,
        # придётся разбирать текст сообщения регулярками.
        event = getattr(record, "event", None)
        if isinstance(event, dict):
            payload.update(event)
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


def setup_logging(level: str | None = None) -> None:
    level_name = (level or os.getenv("LOG_LEVEL") or "INFO").upper()
    LOG_DIR.mkdir(exist_ok=True)

    handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    handler.setFormatter(JsonFormatter())

    root = logging.getLogger()
    root.setLevel(level_name)
    root.addHandler(handler)

    # HTTP-библиотека логирует каждый запрос на DEBUG — на INFO это шум
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)