"""Unit tests for handlers.py."""

from unittest.mock import AsyncMock, MagicMock, patch

from aiogram.exceptions import TelegramForbiddenError

import handlers

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_message(user_id: int = 42) -> AsyncMock:
    msg = AsyncMock()
    msg.from_user = MagicMock(id=user_id)
    msg.answer = AsyncMock()
    return msg


def _make_bot() -> AsyncMock:
    bot = AsyncMock()
    bot.get_file = AsyncMock(return_value=MagicMock(file_path="test/path.ogg"))
    bot.download_file = AsyncMock(return_value=MagicMock(read=MagicMock(return_value=b"")))
    return bot


# ---------------------------------------------------------------------------
# _safe_filename
# ---------------------------------------------------------------------------


def test_safe_filename_normal_name():
    assert handlers._safe_filename("meeting.mp3") == "meeting.mp3"


def test_safe_filename_replaces_slashes_preventing_path_traversal():
    result = handlers._safe_filename("../../etc/passwd")
    assert "/" not in result
    assert "\\" not in result


def test_safe_filename_replaces_spaces():
    assert handlers._safe_filename("my file.ogg") == "my_file.ogg"


def test_safe_filename_replaces_special_chars():
    result = handlers._safe_filename("file;rm -rf *.ogg")
    assert ";" not in result
    assert " " not in result


# ---------------------------------------------------------------------------
# _safe_answer — TelegramForbiddenError must not crash the bot
# ---------------------------------------------------------------------------


async def test_safe_answer_handles_forbidden_silently():
    """When the user has blocked the bot, _safe_answer must not raise."""
    msg = _make_message()
    msg.answer.side_effect = TelegramForbiddenError(
        method=MagicMock(), message="Forbidden: bot was blocked by the user"
    )
    await handlers._safe_answer(msg, "Привет")  # should not raise
    msg.answer.assert_called_once_with("Привет")


# ---------------------------------------------------------------------------
# /start and /help
# ---------------------------------------------------------------------------


async def test_cmd_start_replies():
    msg = _make_message()
    await handlers.cmd_start(msg)
    msg.answer.assert_called_once()
    text = msg.answer.call_args.args[0]
    assert "Meeting Notes Bot" in text


async def test_cmd_help_replies_with_formats():
    msg = _make_message()
    await handlers.cmd_help(msg)
    msg.answer.assert_called_once()
    text = msg.answer.call_args.args[0]
    assert "mp3" in text or "ogg" in text


# ---------------------------------------------------------------------------
# File size limit (25 MB)
# ---------------------------------------------------------------------------


async def test_handle_voice_rejects_oversized_file():
    msg = _make_message()
    msg.voice = MagicMock(
        file_size=26 * 1024 * 1024,
        file_unique_id="uid1",
        file_id="fid1",
        duration=30,
    )
    bot = _make_bot()

    await handlers.handle_voice(msg, bot)

    msg.answer.assert_called_once()
    assert "слишком большой" in msg.answer.call_args.args[0]


async def test_handle_audio_rejects_oversized_file():
    msg = _make_message()
    msg.audio = MagicMock(
        file_size=30 * 1024 * 1024,
        file_unique_id="uid2",
        file_id="fid2",
        file_name="rec.mp3",
        duration=60,
    )
    bot = _make_bot()

    await handlers.handle_audio(msg, bot)

    msg.answer.assert_called_once()
    assert "слишком большой" in msg.answer.call_args.args[0]


# ---------------------------------------------------------------------------
# Duration limit (30 minutes)
# ---------------------------------------------------------------------------


async def test_process_rejects_audio_over_30_minutes():
    msg = _make_message()
    bot = _make_bot()

    with patch("handlers._download", new_callable=AsyncMock):
        await handlers._process(msg, bot, "fid", "test.ogg", duration=31 * 60)

    msg.answer.assert_called_once()
    assert "слишком длинное" in msg.answer.call_args.args[0]


# ---------------------------------------------------------------------------
# Extension allowlist
# ---------------------------------------------------------------------------


async def test_handle_audio_rejects_disallowed_extension():
    msg = _make_message()
    msg.audio = MagicMock(
        file_size=1 * 1024 * 1024,
        file_unique_id="uid3",
        file_id="fid3",
        file_name="malicious.php",
        duration=10,
    )
    bot = _make_bot()

    await handlers.handle_audio(msg, bot)

    msg.answer.assert_called_once()
    assert "не поддерживается" in msg.answer.call_args.args[0]


async def test_handle_audio_accepts_allowed_extension():
    """An .ogg file within limits must proceed to _process (not be rejected early)."""
    msg = _make_message()
    msg.audio = MagicMock(
        file_size=1 * 1024 * 1024,
        file_unique_id="uid4",
        file_id="fid4",
        file_name="meeting.ogg",
        duration=60,
    )
    bot = _make_bot()

    with patch("handlers._process", new_callable=AsyncMock) as mock_process:
        await handlers.handle_audio(msg, bot)

    mock_process.assert_called_once()


# ---------------------------------------------------------------------------
# Unsupported content types
# ---------------------------------------------------------------------------


async def test_handle_unsupported_explains_audio_only():
    msg = _make_message()
    await handlers.handle_unsupported(msg)
    msg.answer.assert_called_once()
    text = msg.answer.call_args.args[0].lower()
    assert "аудио" in text or "голосов" in text
