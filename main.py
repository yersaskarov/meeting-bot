import asyncio
import logging

from aiogram import Bot, Dispatcher

import handlers
from config import BOT_TOKEN
from transcription import executor, load_model

logging.basicConfig(level=logging.INFO)


async def main() -> None:
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN не задан в .env файле")

    loop = asyncio.get_event_loop()
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
    asyncio.run(main())
