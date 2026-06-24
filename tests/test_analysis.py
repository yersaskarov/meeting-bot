"""Unit tests for analysis.py (Claude API)."""

from unittest.mock import AsyncMock, MagicMock, patch

import anthropic
import pytest

import analysis


@pytest.fixture(autouse=True)
def reset_client():
    """Reset the module-level singleton before each test so patches take effect."""
    analysis._client = None
    yield
    analysis._client = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_anthropic_client(text: str = "📋 Саммари: тест"):
    """Return a patched AsyncAnthropic that yields `text`."""
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text=text)]

    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(return_value=mock_response)

    return mock_client


# ---------------------------------------------------------------------------
# Success
# ---------------------------------------------------------------------------


async def test_analyze_returns_claude_response():
    """analyze() returns the text from Claude's response."""
    with patch(
        "analysis.anthropic.AsyncAnthropic", return_value=_mock_anthropic_client("📋 Саммари")
    ):
        result = await analysis.analyze("Обсудили запуск продукта.")

    assert "Саммари" in result


async def test_analyze_sends_correct_prompt():
    """The transcript must appear inside the message sent to Claude."""
    transcript = "Иван взял дизайн до пятницы."
    captured_messages = []

    async def fake_create(**kwargs):
        captured_messages.extend(kwargs.get("messages", []))
        resp = MagicMock()
        resp.content = [MagicMock(text="ok")]
        return resp

    mock_client = AsyncMock()
    mock_client.messages.create = fake_create

    with patch("analysis.anthropic.AsyncAnthropic", return_value=mock_client):
        await analysis.analyze(transcript)

    assert any(transcript in m["content"] for m in captured_messages)


async def test_analyze_uses_system_prompt():
    """A system prompt must be passed to separate instructions from user content."""
    captured_kwargs: list[dict] = []

    async def fake_create(**kwargs):
        captured_kwargs.append(kwargs)
        resp = MagicMock()
        resp.content = [MagicMock(text="ok")]
        return resp

    mock_client = AsyncMock()
    mock_client.messages.create = fake_create

    with patch("analysis.anthropic.AsyncAnthropic", return_value=mock_client):
        await analysis.analyze("Meeting transcript.")

    assert captured_kwargs, "messages.create was never called"
    assert "system" in captured_kwargs[0], "system prompt must be set to isolate user content"
    assert captured_kwargs[0]["system"], "system prompt must not be empty"


# ---------------------------------------------------------------------------
# Error propagation — handlers.py catches these, so they must propagate cleanly
# ---------------------------------------------------------------------------


async def test_analyze_propagates_rate_limit_error():
    """RateLimitError from Claude must propagate so handlers can catch it."""
    mock_client = AsyncMock()
    mock_client.messages.create.side_effect = anthropic.RateLimitError(
        message="rate limit", response=MagicMock(), body={}
    )
    with (
        patch("analysis.anthropic.AsyncAnthropic", return_value=mock_client),
        pytest.raises(anthropic.RateLimitError),
    ):
        await analysis.analyze("Текст митинга.")


async def test_analyze_propagates_api_status_error_500():
    """APIStatusError (e.g. 500) must propagate so handlers can catch it."""
    mock_client = AsyncMock()
    mock_client.messages.create.side_effect = anthropic.APIStatusError(
        message="internal error",
        response=MagicMock(status_code=500),
        body={},
    )
    with (
        patch("analysis.anthropic.AsyncAnthropic", return_value=mock_client),
        pytest.raises(anthropic.APIStatusError),
    ):
        await analysis.analyze("Текст митинга.")


# ---------------------------------------------------------------------------
# Edge-case inputs
# ---------------------------------------------------------------------------


async def test_analyze_handles_long_transcript():
    """analyze() must accept a 50 000-char transcript without error."""
    long_text = "слово " * 8_333  # ~50 000 chars
    client = _mock_anthropic_client("📋 Саммари длинного митинга")

    with patch("analysis.anthropic.AsyncAnthropic", return_value=client):
        result = await analysis.analyze(long_text)

    assert result  # not empty


async def test_analyze_handles_single_word():
    """analyze() works with a one-word transcript."""
    client = _mock_anthropic_client("📋 Саммари: одно слово")

    with patch("analysis.anthropic.AsyncAnthropic", return_value=client):
        result = await analysis.analyze("Привет")

    assert result
