"""Unit tests for formatter.py — parse_analysis and format_parsed."""

from formatter import format_for_telegram, format_parsed, parse_analysis

_DIVIDER = "━━━━━━━━━━━━━━"

# ---------------------------------------------------------------------------
# parse_analysis
# ---------------------------------------------------------------------------


def test_parse_analysis_valid_json() -> None:
    raw = '{"summary": "Good meeting", "tasks": [], "deadlines": [], "notes": ""}'
    data = parse_analysis(raw)
    assert data["summary"] == "Good meeting"
    assert data["tasks"] == []


def test_parse_analysis_strips_markdown_fences() -> None:
    raw = '```json\n{"summary": "ok", "tasks": [], "deadlines": [], "notes": ""}\n```'
    data = parse_analysis(raw)
    assert data["summary"] == "ok"


def test_parse_analysis_fallback_on_invalid_json() -> None:
    raw = "Некорректный JSON ответ"
    data = parse_analysis(raw)
    assert data["summary"] == "Некорректный JSON ответ"
    assert data["tasks"] == []
    assert data["deadlines"] == []
    assert data["notes"] == ""


def test_parse_analysis_fallback_on_empty_string() -> None:
    data = parse_analysis("")
    assert data["summary"] == ""


# ---------------------------------------------------------------------------
# format_parsed — summary only
# ---------------------------------------------------------------------------


def test_format_parsed_summary_appears() -> None:
    data = {"summary": "Обсудили дедлайны.", "tasks": [], "deadlines": [], "notes": ""}
    result = format_parsed(data)
    assert "Обсудили дедлайны." in result
    assert "📋" in result


def test_format_parsed_empty_data_returns_empty_string() -> None:
    result = format_parsed({"summary": "", "tasks": [], "deadlines": [], "notes": ""})
    assert result == ""


# ---------------------------------------------------------------------------
# format_parsed — tasks
# ---------------------------------------------------------------------------


def test_format_parsed_tasks_with_owner() -> None:
    data = {
        "summary": "",
        "tasks": [{"owner": "Ерсултан", "task": "Подготовить отчёт"}],
        "deadlines": [],
        "notes": "",
    }
    result = format_parsed(data)
    assert "Ерсултан" in result
    assert "Подготовить отчёт" in result
    assert "✅" in result
    assert "👤" in result


def test_format_parsed_tasks_without_owner() -> None:
    data = {
        "summary": "",
        "tasks": [{"owner": "", "task": "Позвонить клиенту"}],
        "deadlines": [],
        "notes": "",
    }
    result = format_parsed(data)
    assert "Позвонить клиенту" in result
    assert "👤" not in result


def test_format_parsed_tasks_grouped_by_owner() -> None:
    data = {
        "summary": "",
        "tasks": [
            {"owner": "Иван", "task": "Дизайн"},
            {"owner": "Иван", "task": "Презентация"},
            {"owner": "Мария", "task": "Тесты"},
        ],
        "deadlines": [],
        "notes": "",
    }
    result = format_parsed(data)
    ivan_pos = result.index("Иван")
    maria_pos = result.index("Мария")
    dizain_pos = result.index("Дизайн")
    prezent_pos = result.index("Презентация")
    assert ivan_pos < dizain_pos < prezent_pos < maria_pos


def test_format_parsed_skips_tasks_with_empty_task_field() -> None:
    data = {
        "summary": "Summary",
        "tasks": [{"owner": "Alice", "task": ""}],
        "deadlines": [],
        "notes": "",
    }
    result = format_parsed(data)
    assert "✅" not in result


# ---------------------------------------------------------------------------
# format_parsed — deadlines
# ---------------------------------------------------------------------------


def test_format_parsed_deadlines_appear() -> None:
    data = {
        "summary": "",
        "tasks": [],
        "deadlines": [{"task": "Отчёт", "date": "До пятницы"}],
        "notes": "",
    }
    result = format_parsed(data)
    assert "📅" in result
    assert "📌" in result
    assert "Отчёт" in result
    assert "До пятницы" in result
    assert "🗓" in result


# ---------------------------------------------------------------------------
# format_parsed — notes
# ---------------------------------------------------------------------------


def test_format_parsed_notes_appear() -> None:
    data = {"summary": "", "tasks": [], "deadlines": [], "notes": "Рекомендация: указывать даты"}
    result = format_parsed(data)
    assert "💡" in result
    assert "Рекомендация" in result


def test_format_parsed_empty_notes_not_shown() -> None:
    data = {"summary": "S", "tasks": [], "deadlines": [], "notes": ""}
    result = format_parsed(data)
    assert "💡" not in result


# ---------------------------------------------------------------------------
# format_parsed — dividers between sections
# ---------------------------------------------------------------------------


def test_format_parsed_divider_between_sections() -> None:
    data = {
        "summary": "Саммари",
        "tasks": [{"owner": "", "task": "Задача"}],
        "deadlines": [],
        "notes": "",
    }
    result = format_parsed(data)
    assert _DIVIDER in result


def test_format_parsed_no_divider_when_single_section() -> None:
    data = {"summary": "Только саммари", "tasks": [], "deadlines": [], "notes": ""}
    result = format_parsed(data)
    assert _DIVIDER not in result


# ---------------------------------------------------------------------------
# format_for_telegram — backward-compat wrapper
# ---------------------------------------------------------------------------


def test_format_for_telegram_falls_back_to_raw_on_empty_result() -> None:
    raw = "Сырой текст без JSON"
    result = format_for_telegram(raw)
    assert "Сырой текст без JSON" in result


def test_format_for_telegram_parses_and_formats_json() -> None:
    raw = '{"summary": "Итог встречи", "tasks": [], "deadlines": [], "notes": ""}'
    result = format_for_telegram(raw)
    assert "Итог встречи" in result
    assert "📋" in result
