import asyncio
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from aiogram import Bot, Dispatcher

import handlers
import storage
from config import BOT_TOKEN
from transcription import check_ffmpeg, executor, load_model


def setup_logging() -> None:
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")

    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(fmt)

    Path("logs").mkdir(exist_ok=True)
    file_handler = RotatingFileHandler("logs/errors.log", maxBytes=5 * 1024 * 1024, backupCount=2)
    file_handler.setLevel(logging.ERROR)
    file_handler.setFormatter(fmt)

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(console)
    root.addHandler(file_handler)


async def main() -> None:
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN is not set in .env")

    storage.init_db()
    check_ffmpeg()

    loop = asyncio.get_running_loop()
    await loop.run_in_executor(executor, load_model)

    dp = Dispatcher()
    handlers.register(dp)

    bot = Bot(token=BOT_TOKEN)
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        executor.shutdown(wait=False)


if __name__ == "__main__":
    setup_logging()
    asyncio.run(main())
