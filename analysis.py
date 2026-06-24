import logging

import anthropic

from config import ANTHROPIC_API_KEY

logger = logging.getLogger(__name__)

ANALYSIS_PROMPT = (
    "Ты помощник для анализа митингов. Из текста ниже выдели:\n"
    "1. 📋 Краткое саммари (3-5 предложений)\n"
    "2. ✅ Список задач с ответственными (если упомянуты)\n"
    "3. 📅 Дедлайны и договорённости\n"
    "Отвечай на том же языке что и текст."
)


async def analyze(transcript: str) -> str:
    client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
    response = await client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        messages=[{"role": "user", "content": f"{ANALYSIS_PROMPT}\n\nТекст:\n{transcript}"}],
    )
    return response.content[0].text
