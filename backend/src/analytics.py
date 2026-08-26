"""Аналитика пользовательских запросов по логу.

Запуск в консоли:
    .venv/bin/python -m src.analytics

Тот же результат отдаётся ручкой GET /api/analytics (только роли staff).
Считает всё summarize() — и консоль, и API берут цифры из него, чтобы отчёт
на экране и в терминале не разъехались.

Читает logs/app.log, берёт только сводные записи (event="ask") — по одной на
каждый заданный вопрос.

Пустые ответы важнее всего: это вопросы, на которые система формально
отработала, но пользователю не помогла — именно их стоит чинить в первую очередь.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

LOG_FILE = Path(__file__).resolve().parent.parent / "logs" / "app.log"

# Сколько последних обращений показывать в ленте.
RECENT_LIMIT = 50


def load_events(path: Path = LOG_FILE) -> list[dict]:
    if not path.exists():
        return []
    events = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if record.get("event") == "ask":
            events.append(record)
    return events


def _percentile(values: list[int], share: float) -> int:
    if not values:
        return 0
    ordered = sorted(values)
    index = min(int(len(ordered) * share), len(ordered) - 1)
    return ordered[index]


def summarize(events: list[dict]) -> dict:
    """Сводка по логу в виде данных — для API и для консольного отчёта."""
    if not events:
        return {
            "total": 0,
            "by_role": {},
            "by_outcome": {},
            "timing": {"median_ms": 0, "p95_ms": 0, "max_ms": 0},
            "empty_results": [],
            "blocked": [],
            "top_questions": [],
            "recent": [],
        }

    durations = [event.get("elapsed_ms", 0) for event in events]

    empty_results = [
        event for event in events if event.get("outcome") == "ok" and event.get("row_count") == 0
    ]
    blocked = [event for event in events if event.get("outcome") in ("forbidden", "refused")]

    def slim(event: dict) -> dict:
        # student_id намеренно не отдаём: для аналитики он не нужен, а вопрос
        # вида «есть ли у меня задолженности» вместе с ним уже раскрывает человека.
        return {
            "time": event.get("time"),
            "role": event.get("role"),
            "question": event.get("question"),
            "outcome": event.get("outcome"),
            "row_count": event.get("row_count"),
            "elapsed_ms": event.get("elapsed_ms"),
            "sql": event.get("sql"),
        }

    return {
        "total": len(events),
        "by_role": dict(Counter(e.get("role") or "—" for e in events).most_common()),
        "by_outcome": dict(Counter(e.get("outcome") or "—" for e in events).most_common()),
        "timing": {
            "median_ms": _percentile(durations, 0.5),
            "p95_ms": _percentile(durations, 0.95),
            "max_ms": max(durations),
        },
        "empty_results": [slim(e) for e in empty_results[-10:]],
        "blocked": [slim(e) for e in blocked[-10:]],
        "top_questions": [
            {"question": question, "count": count}
            for question, count in Counter(e.get("question") for e in events).most_common(5)
        ],
        "recent": [slim(e) for e in reversed(events[-RECENT_LIMIT:])],
    }


def report(events: list[dict]) -> str:
    """Текстовый отчёт для консоли — по тем же цифрам, что уходят в API."""
    data = summarize(events)
    if not data["total"]:
        return "В логе пока нет ни одного запроса (logs/app.log)."

    lines = [f"Всего вопросов: {data['total']}", "", "По ролям:"]
    for role, count in data["by_role"].items():
        lines.append(f"  {role:12} {count}")

    lines.append("")
    lines.append("Чем закончилось:")
    for outcome, count in data["by_outcome"].items():
        share = count / data["total"] * 100
        lines.append(f"  {outcome:12} {count:4}  ({share:.0f}%)")

    timing = data["timing"]
    lines.append("")
    lines.append("Время ответа:")
    lines.append(f"  медиана    {timing['median_ms']} мс")
    lines.append(f"  95-й проц. {timing['p95_ms']} мс")
    lines.append(f"  максимум   {timing['max_ms']} мс")

    if data["empty_results"]:
        lines.append("")
        lines.append(
            f"Отработали, но вернули пусто ({len(data['empty_results'])}) — "
            "что чинить в первую очередь:"
        )
        for event in data["empty_results"]:
            lines.append(f"  — {event['question']}")

    if data["blocked"]:
        lines.append("")
        lines.append(f"Отклонено ({len(data['blocked'])}):")
        for event in data["blocked"]:
            lines.append(f"  — [{event['role']}] {event['question']}")

    lines.append("")
    lines.append("Самые частые вопросы:")
    for item in data["top_questions"]:
        lines.append(f"  {item['count']}x  {item['question']}")

    return "\n".join(lines)


if __name__ == "__main__":
    print(report(load_events()))
