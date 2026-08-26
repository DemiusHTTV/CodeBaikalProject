"""Аналитика пользовательских запросов по логу.

Запуск (из backend/):
    .venv/bin/python -m src.analytics

Читает logs/app.log, берёт только сводные записи (event="ask") — по одной на
каждый заданный вопрос — и считает по ним статистику: кто чем пользуется, что
отклоняется защитой, где тормозит, какие вопросы возвращают пусто.

Пустые ответы важнее всего: это вопросы, на которые система формально
отработала, но пользователю не помогла — именно их стоит чинить в первую очередь.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

LOG_FILE = Path(__file__).resolve().parent.parent / "logs" / "app.log"


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


def report(events: list[dict]) -> str:
    if not events:
        return "В логе пока нет ни одного запроса (logs/app.log)."

    lines = [f"Всего вопросов: {len(events)}", ""]

    lines.append("По ролям:")
    for role, count in Counter(e.get("role") for e in events).most_common():
        lines.append(f"  {role or '—':12} {count}")

    lines.append("")
    lines.append("Чем закончилось:")
    for outcome, count in Counter(e.get("outcome") for e in events).most_common():
        share = count / len(events) * 100
        lines.append(f"  {outcome or '—':12} {count:4}  ({share:.0f}%)")

    durations = [e.get("elapsed_ms", 0) for e in events]
    lines.append("")
    lines.append("Время ответа:")
    lines.append(f"  медиана  {_percentile(durations, 0.5)} мс")
    lines.append(f"  95-й проц. {_percentile(durations, 0.95)} мс")
    lines.append(f"  максимум {max(durations)} мс")

    empty = [e for e in events if e.get("outcome") == "ok" and e.get("row_count") == 0]
    if empty:
        lines.append("")
        lines.append(f"Отработали, но вернули пусто ({len(empty)}) — что чинить в первую очередь:")
        for event in empty[:10]:
            lines.append(f"  — {event.get('question')}")

    blocked = [e for e in events if e.get("outcome") == "forbidden"]
    if blocked:
        lines.append("")
        lines.append(f"Отклонено защитой ({len(blocked)}):")
        for event in blocked[:10]:
            lines.append(f"  — [{event.get('role')}] {event.get('question')}")

    lines.append("")
    lines.append("Самые частые вопросы:")
    for question, count in Counter(e.get("question") for e in events).most_common(5):
        lines.append(f"  {count}x  {question}")

    return "\n".join(lines)


if __name__ == "__main__":
    print(report(load_events()))
