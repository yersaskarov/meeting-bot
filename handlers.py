import logging
from pathlib import Path

import aiofiles
import anthropic
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from analysis import analyze
from config import ANTHROPIC_API_KEY
from transcription import transcribe

logger = logging.getLogger(__name__)

AUDIO_DIR = Path("audio")
AUDIO_DIR.mkdir(exist_ok=True)


async def _download(bot: Bot, file_id: str, dest: Path) -> None:
    file = await bot.get_file(file_id)
    data = await bot.download_file(file.file_path)
    async with aiofiles.open(dest, "wb") as f:
        await f.write(data.read())


async def _process(message: Message, bot: Bot, file_id: str, file_name: str) -> None:
    file_path = AUDIO_DIR / file_name
    await _download(bot, file_id, file_path)
    logger.info("Saved %s from user %s", file_name, message.from_user.id)

    # Step 1: transcribe with Whisper
    await message.answer("⏳ Транскрибирую аудио...")
    try:
        transcript = await transcribe(file_path)
    except Exception as e:
        logger.error("Whisper error: %s", e)
        await message.answer(
            "❌ Не удалось транскрибировать аудио.\n"
            "Убедись, что файл содержит речь и имеет поддерживаемый формат (ogg, mp3, wav, m4a)."
        )
        return

    if not transcript:
        await message.answer("⚠️ В аудио не обнаружена речь.")
        return

    await message.answer(f"📝 *Транскрипт:*\n\n{transcript}", parse_mode="Markdown")

    # Step 2: analyze with Claude
    if not ANTHROPIC_API_KEY or ANTHROPIC_API_KEY == "your_anthropic_api_key_here":
        await message.answer("⚠️ ANTHROPIC\\_API\\_KEY не настроен — анализ недоступен.", parse_mode="Markdown")
        return

    await message.answer("🧠 Анализирую...")
    try:
        result = await analyze(transcript)
    except anthropic.AuthenticationError:
        await message.answer("❌ Неверный ANTHROPIC\\_API\\_KEY\\. Проверь ключ в `.env`\\.", parse_mode="MarkdownV2")
        return
    except anthropic.APIConnectionError:
        await message.answer("❌ Нет соединения с Claude API. Попробуй позже.")
        return
    except Exception as e:
        logger.error("Claude error: %s", e)
        await message.answer("❌ Ошибка при анализе через Claude. Попробуй позже.")
        return

    await message.answer(result)


async def cmd_start(message: Message) -> None:
    await message.answer(
        "👋 Привет! Я *Meeting Notes Bot*.\n\n"
        "Что я умею:\n"
        "🎤 Принимаю голосовые сообщения и аудиофайлы\n"
        "📝 Транскрибирую речь в текст через Whisper\n"
        "🧠 Анализирую митинг через Claude AI\n"
        "✅ Выделяю задачи, ответственных и дедлайны\n\n"
        "Просто отправь голосовое или аудиофайл — остальное сделаю я.",
        parse_mode="Markdown",
    )


async def cmd_help(message: Message) -> None:
    await message.answer(
        "📖 *Как пользоваться:*\n\n"
        "1. Запиши голосовое или отправь аудиофайл\n"
        "2. Дождись транскрипции (~30 сек на 5 минут аудио)\n"
        "3. Получи транскрипт, саммари, задачи и дедлайны\n\n"
        "*Форматы:* ogg, mp3, wav, m4a, mp4\n"
        "*Языки:* русский, английский (автоопределение)\n\n"
        "/start — главное меню",
        parse_mode="Markdown",
    )


async def handle_voice(message: Message, bot: Bot) -> None:
    voice = message.voice
    file_name = f"voice_{message.from_user.id}_{voice.file_unique_id}.ogg"
    await _process(message, bot, voice.file_id, file_name)


async def handle_audio(message: Message, bot: Bot) -> None:
    audio = message.audio
    original = audio.file_name or f"audio_{audio.file_unique_id}"
    ext = Path(original).suffix or ".mp3"
    file_name = f"audio_{message.from_user.id}_{audio.file_unique_id}{ext}"
    await _process(message, bot, audio.file_id, file_name)


def register(dp: Dispatcher) -> None:
    dp.message.register(cmd_start, CommandStart())
    dp.message.register(cmd_help, Command("help"))
    dp.message.register(handle_voice, F.voice)
    dp.message.register(handle_audio, F.audio)
