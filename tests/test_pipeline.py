"""Integration tests for the full audio → transcript → analysis pipeline."""

from unittest.mock import AsyncMock, MagicMock, patch

import anthropic

import handlers

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_message(user_id: int = 99) -> AsyncMock:
    msg = AsyncMock()
    msg.from_user = MagicMock(id=user_id)
    msg.answer = AsyncMock()
    return msg


def _make_bot() -> AsyncMock:
    return AsyncMock()


def _answered_texts(msg: AsyncMock) -> list[str]:
    return [call.args[0] for call in msg.answer.call_args_list if call.args]


# ---------------------------------------------------------------------------
# Full pipeline success
# ---------------------------------------------------------------------------


async def test_full_pipeline_audio_to_analysis():
    """
    Full flow: file received → downloaded → transcribed → analysed → 4 replies sent.
    All external calls are mocked.
    """
    msg = _make_message()
    bot = _make_bot()

    with (
        patch("handlers._download", new_callable=AsyncMock),
        patch(
            "handlers.transcribe", new_callable=AsyncMock, return_value="Обсудили дедлайны."
        ) as mock_tr,
        patch(
            "handlers.analyze", new_callable=AsyncMock, return_value="📋 Саммари: дедлайны"
        ) as mock_an,
        patch("handlers.ANTHROPIC_API_KEY", "sk-ant-test"),
        patch("handlers.storage.save_meeting"),
    ):
        await handlers._process(msg, bot, "fid", "voice_99_uid.ogg", duration=120)

    mock_tr.assert_called_once()
    mock_an.assert_called_once_with("Обсудили дедлайны.")

    texts = _answered_texts(msg)
    assert any("⏳" in t for t in texts), "должно быть сообщение о начале транскрипции"
    assert any("Обсудили дедлайны" in t for t in texts), "транскрипт должен быть отправлен"
    assert any("🧠" in t for t in texts), "должно быть сообщение об анализе"
    assert any("Саммари" in t for t in texts), "результат анализа должен быть отправлен"


# ---------------------------------------------------------------------------
# Whisper fails
# ---------------------------------------------------------------------------


async def test_pipeline_whisper_failure_sends_error_and_does_not_crash():
    """If Whisper throws, bot sends an error message and does not crash."""
    msg = _make_message()
    bot = _make_bot()

    with (
        patch("handlers._download", new_callable=AsyncMock),
        patch("handlers.transcribe", side_effect=RuntimeError("CUDA out of memory")),
    ):
        await handlers._process(msg, bot, "fid", "voice_99_uid.ogg", duration=60)

    texts = _answered_texts(msg)
    assert any("❌" in t for t in texts), "пользователь должен получить сообщение об ошибке"
    assert not any("🧠" in t for t in texts), "анализ не должен запускаться после ошибки"


# ---------------------------------------------------------------------------
# Transcription timeout
# ---------------------------------------------------------------------------


async def test_pipeline_transcription_timeout_notifies_user():
    """If transcription exceeds 5 min, user gets a timeout message."""
    msg = _make_message()
    bot = _make_bot()

    with (
        patch("handlers._download", new_callable=AsyncMock),
        patch("handlers.asyncio.wait_for", side_effect=TimeoutError()),
    ):
        await handlers._process(msg, bot, "fid", "voice_99_uid.ogg", duration=60)

    texts = _answered_texts(msg)
    assert any("долго" in t or "timeout" in t.lower() or "мин" in t for t in texts)


# ---------------------------------------------------------------------------
# Claude fails
# ---------------------------------------------------------------------------


async def test_pipeline_claude_rate_limit_sends_friendly_message():
    """If Claude returns RateLimitError, user sees a friendly retry message."""
    msg = _make_message()
    bot = _make_bot()

    with (
        patch("handlers._download", new_callable=AsyncMock),
        patch("handlers.transcribe", new_callable=AsyncMock, return_value="Текст митинга"),
        patch(
            "handlers.analyze",
            new_callable=AsyncMock,
            side_effect=anthropic.RateLimitError(
                message="rate limit", response=MagicMock(), body={}
            ),
        ),
        patch("handlers.ANTHROPIC_API_KEY", "sk-ant-test"),
    ):
        await handlers._process(msg, bot, "fid", "voice_99_uid.ogg", duration=60)

    texts = _answered_texts(msg)
    assert any("перегруж" in t.lower() or "rate" in t.lower() or "минут" in t for t in texts)


async def test_pipeline_claude_api_error_sends_error_message():
    """If Claude returns APIStatusError 500, user sees an error message."""
    msg = _make_message()
    bot = _make_bot()

    async def fake_transcribe(_path):
        return "Текст митинга"

    async def fake_analyze(_text):
        raise anthropic.APIStatusError(
            message="internal error",
            response=MagicMock(status_code=500),
            body={},
        )

    with (
        patch("handlers._download", new_callable=AsyncMock),
        patch("handlers.transcribe", fake_transcribe),
        patch("handlers.analyze", fake_analyze),
        patch("handlers.ANTHROPIC_API_KEY", "sk-ant-test"),
    ):
        await handlers._process(msg, bot, "fid", "voice_99_uid.ogg", duration=60)

    texts = _answered_texts(msg)
    assert any("❌" in t or "500" in t for t in texts)
