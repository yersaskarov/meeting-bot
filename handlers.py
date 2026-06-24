import asyncio
import contextlib
import logging
import re
from pathlib import Path

import aiofiles
import anthropic
from aiogram import Bot, Dispatcher, F
from aiogram.exceptions import TelegramForbiddenError
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from analysis import analyze
from config import ANTHROPIC_API_KEY
from transcription import transcribe

logger = logging.getLogger(__name__)

AUDIO_DIR = Path("audio")
AUDIO_DIR.mkdir(exist_ok=True)

MAX_FILE_SIZE = 25 * 1024 * 1024
MAX_DURATION = 30 * 60
MAX_TRANSCRIPT_CHARS = 50_000
TRANSCRIPTION_TIMEOUT = 300

ALLOWED_EXTENSIONS = frozenset({".ogg", ".mp3", ".wav", ".m4a", ".mp4", ".flac", ".opus"})


def _safe_filename(name: str) -> str:
    return re.sub(r"[^\w.-]", "_", name)


async def _safe_answer(message: Message, text: str, **kwargs) -> None:
    try:
        await message.answer(text, **kwargs)
    except TelegramForbiddenError:
        assert message.from_user is not None
        logger.warning("User %s has blocked the bot — skipping reply", message.from_user.id)


async def _download(bot: Bot, file_id: str, dest: Path) -> None:
    file = await bot.get_file(file_id)
    assert file.file_path is not None
    data = await bot.download_file(file.file_path)
    assert data is not None
    async with aiofiles.open(dest, "wb") as f:
        await f.write(data.read())


async def _process(
    message: Message,
    bot: Bot,
    file_id: str,
    file_name: str,
    duration: int | None = None,
) -> None:
    if duration is not None and duration > MAX_DURATION:
        await _safe_answer(
            message,
            f"⚠️ Аудио слишком длинное ({duration // 60} мин {duration % 60} сек).\n"
            f"Максимум — 30 минут.",
        )
        return

    file_path = AUDIO_DIR / _safe_filename(file_name)

    try:
        await _download(bot, file_id, file_path)
    except OSError as e:
        logger.error("Disk error saving %s: %s", file_name, e)
        await _safe_answer(
            message, "❌ Не удалось сохранить файл. Возможно, закончилось место на диске."
        )
        return

    assert message.from_user is not None
    logger.info("Saved %s from user %s", file_name, message.from_user.id)

    await _safe_answer(message, "⏳ Транскрибирую аудио... это может занять до 2 минут")
    logger.info(
        "Calling transcribe: path=%s exists=%s size=%s",
        file_path,
        file_path.exists(),
        file_path.stat().st_size if file_path.exists() else "N/A",
    )
    try:
        transcript = await asyncio.wait_for(transcribe(file_path), timeout=TRANSCRIPTION_TIMEOUT)
    except TimeoutError:
        logger.error("Transcription timeout for %s", file_name)
        await _safe_answer(
            message,
            "❌ Транскрипция заняла слишком долго (>5 мин).\n"
            "Попробуй файл покороче или с более чёткой речью.",
        )
        return
    except Exception:
        logger.exception("Whisper error for %s", file_name)
        await _safe_answer(
            message,
            "❌ Не удалось транскрибировать аудио.\n"
            "Убедись, что файл содержит речь и имеет поддерживаемый формат (ogg, mp3, wav, m4a).",
        )
        return
    finally:
        with contextlib.suppress(OSError):
            file_path.unlink(missing_ok=True)

    if not transcript or len(transcript.strip()) < 3:
        await _safe_answer(message, "⚠️ В аудио не обнаружена речь или текст слишком короткий.")
        return

    truncated = len(transcript) > MAX_TRANSCRIPT_CHARS
    if truncated:
        transcript = transcript[:MAX_TRANSCRIPT_CHARS]

    transcript_msg = f"📝 *Транскрипт:*\n\n{transcript}"
    if truncated:
        transcript_msg += "\n\n_⚠️ Текст обрезан — аудио слишком длинное_"
    await _safe_answer(message, transcript_msg, parse_mode="Markdown")

    if not ANTHROPIC_API_KEY or ANTHROPIC_API_KEY == "your_anthropic_api_key_here":
        await _safe_answer(message, "⚠️ ANTHROPIC_API_KEY не настроен — анализ недоступен.")
        return

    await _safe_answer(message, "🧠 Анализирую...")
    try:
        result = await analyze(transcript)
    except anthropic.AuthenticationError:
        logger.error("Anthropic authentication error")
        await _safe_answer(message, "❌ Неверный ключ Claude API. Обратитесь к администратору.")
        return
    except anthropic.RateLimitError:
        logger.error("Anthropic rate limit exceeded")
        await _safe_answer(message, "⏳ Claude API перегружен. Подожди минуту и попробуй снова.")
        return
    except anthropic.APIStatusError as e:
        logger.error("Anthropic API status error %s: %s", e.status_code, e.message)
        if e.status_code == 529:
            await _safe_answer(message, "⏳ Claude API перегружен. Попробуй через несколько минут.")
        else:
            await _safe_answer(
                message, f"❌ Ошибка Claude API (код {e.status_code}). Попробуй позже."
            )
        return
    except anthropic.APIConnectionError:
        logger.error("Anthropic connection error")
        await _safe_answer(
            message, "❌ Нет соединения с Claude API. Проверь интернет и попробуй позже."
        )
        return
    except Exception as e:
        logger.error("Unexpected Claude error: %s", e)
        await _safe_answer(message, "❌ Неожиданная ошибка при анализе. Попробуй позже.")
        return

    await _safe_answer(message, result)


async def cmd_start(message: Message) -> None:
    await _safe_answer(
        message,
        "👋 Привет! Я *Meeting Notes Bot*.\n\n"
        "Отправь запись встречи — и я:\n"
        "📝 Транскрибирую речь в текст\n"
        "🧠 Выделю саммари, задачи и дедлайны\n\n"
        "*Как использовать:*\n"
        "Нажми 🎤 и запиши голосовое, или прикрепи аудиофайл (mp3, ogg, wav, m4a).\n\n"
        "Максимум: 25 MB и 30 минут.\n"
        "/help — подробная справка",
        parse_mode="Markdown",
    )


async def cmd_help(message: Message) -> None:
    await _safe_answer(
        message,
        "📖 *Meeting Notes Bot — справка*\n\n"
        "*Что принимает бот:*\n"
        "• Голосовые сообщения Telegram\n"
        "• Аудиофайлы: ogg, mp3, wav, m4a, mp4\n"
        "• Максимальный размер: 25 MB\n"
        "• Максимальная длина: 30 минут\n\n"
        "*Что возвращает бот:*\n"
        "1. 📝 Полный транскрипт речи\n"
        "2. 📋 Краткое саммари (3–5 предложений)\n"
        "3. ✅ Задачи с ответственными\n"
        "4. 📅 Дедлайны и договорённости\n\n"
        "*Поддерживаемые языки:* русский, английский (автоопределение)\n\n"
        "*Команды:*\n"
        "/start — главное меню\n"
        "/help — эта справка",
        parse_mode="Markdown",
    )


async def handle_voice(message: Message, bot: Bot) -> None:
    assert message.voice is not None and message.from_user is not None
    voice = message.voice
    if voice.file_size and voice.file_size > MAX_FILE_SIZE:
        size_mb = voice.file_size // 1024 // 1024
        await _safe_answer(message, f"⚠️ Файл слишком большой ({size_mb} MB). Максимум — 25 MB.")
        return
    file_name = f"voice_{message.from_user.id}_{voice.file_unique_id}.ogg"
    await _process(message, bot, voice.file_id, file_name, duration=voice.duration)


async def handle_audio(message: Message, bot: Bot) -> None:
    assert message.audio is not None and message.from_user is not None
    audio = message.audio
    if audio.file_size and audio.file_size > MAX_FILE_SIZE:
        size_mb = audio.file_size // 1024 // 1024
        await _safe_answer(message, f"⚠️ Файл слишком большой ({size_mb} MB). Максимум — 25 MB.")
        return
    original = audio.file_name or f"audio_{audio.file_unique_id}"
    ext = Path(original).suffix.lower() or ".mp3"
    if ext not in ALLOWED_EXTENSIONS:
        await _safe_answer(
            message,
            f"⚠️ Формат `{ext}` не поддерживается.\n"
            "Поддерживаемые форматы: ogg, mp3, wav, m4a, mp4, flac, opus.",
        )
        return
    file_name = f"audio_{message.from_user.id}_{audio.file_unique_id}{ext}"
    await _process(message, bot, audio.file_id, file_name, duration=audio.duration)


async def handle_unsupported(message: Message) -> None:
    await _safe_answer(
        message,
        "🎤 Я принимаю только голосовые сообщения и аудиофайлы.\n\n"
        "Отправь голосовое сообщение или прикрепи аудиофайл (mp3, ogg, wav, m4a).\n"
        "/help — подробная справка",
    )


def register(dp: Dispatcher) -> None:
    dp.message.register(cmd_start, CommandStart())
    dp.message.register(cmd_help, Command("help"))
    dp.message.register(handle_voice, F.voice)
    dp.message.register(handle_audio, F.audio)
    dp.message.register(
        handle_unsupported,
        F.video | F.photo | F.document | F.sticker | F.animation | F.video_note,
    )
