"""Format Claude's JSON analysis response into a readable Telegram message."""

import json
from typing import Any

_DIVIDER = "━━━━━━━━━━━━━━"


def _parse(raw: str) -> dict[str, Any]:
    text = raw.strip()
    # Strip markdown code fences if Claude wraps output despite instructions
    if text.startswith("```"):
        lines = text.splitlines()
        end = next((i for i in range(len(lines) - 1, 0, -1) if lines[i].strip() == "```"), None)
        inner_lines = lines[1:end] if end else lines[1:]
        text = "\n".join(inner_lines).strip()
    try:
        result = json.loads(text)
        if isinstance(result, dict):
            return result
    except (json.JSONDecodeError, ValueError):
        pass
    # Fallback: show the raw text as the summary so nothing is lost
    return {"summary": raw.strip(), "tasks": [], "deadlines": [], "notes": ""}


def parse_analysis(raw: str) -> dict[str, Any]:
    """Parse Claude's JSON response string into a structured dict.

    Returns a dict with keys: summary, tasks, deadlines, notes.
    Never raises — falls back to wrapping the raw string in summary.
    """
    return _parse(raw)


def format_parsed(data: dict[str, Any]) -> str:
    """Format a pre-parsed meeting data dict into a Telegram-ready message.

    Accepts the same shape returned by parse_analysis().
    Returns an empty string when all fields are empty.
    """
    sections: list[str] = []

    summary = (data.get("summary") or "").strip()
    if summary:
        sections.append(f"📋 Краткое резюме\n\n{summary}")

    raw_tasks: list[Any] = data.get("tasks") or []
    tasks = [t for t in raw_tasks if isinstance(t, dict) and (t.get("task") or "").strip()]
    if tasks:
        by_owner: dict[str, list[str]] = {}
        for item in tasks:
            owner = (item.get("owner") or "").strip()
            by_owner.setdefault(owner, []).append(item["task"].strip())

        lines: list[str] = ["✅ Задачи"]
        for owner, owner_tasks in by_owner.items():
            if owner:
                lines.append(f"\n👤 {owner}")
            for t in owner_tasks:
                lines.append(f"\n• {t}")
        sections.append("\n".join(lines))

    raw_deadlines: list[Any] = data.get("deadlines") or []
    deadlines = [d for d in raw_deadlines if isinstance(d, dict)]
    if deadlines:
        lines = ["📅 Дедлайны"]
        for item in deadlines:
            task = (item.get("task") or "").strip()
            date = (item.get("date") or "").strip()
            if task:
                lines.append(f"\n📌 {task}")
            if date:
                lines.append(f"🗓 {date}")
        sections.append("\n".join(lines))

    notes = (data.get("notes") or "").strip()
    if notes:
        sections.append(f"💡 Примечание\n\n{notes}")

    if not sections:
        return ""

    sep = f"\n\n{_DIVIDER}\n\n"
    return sep.join(sections)


def format_for_telegram(raw: str) -> str:
    """Convert Claude's JSON response string into a beautifully formatted Telegram message."""
    data = _parse(raw)
    return format_parsed(data) or raw.strip()
