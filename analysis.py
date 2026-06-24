import logging

import anthropic

from config import ANTHROPIC_API_KEY, CLAUDE_MODEL

logger = logging.getLogger(__name__)

# Instructions in system prompt so they cannot be overridden by user-supplied transcript content.
_SYSTEM_PROMPT = (
    "You are a meeting analysis assistant. "
    "Extract structured information from meeting transcripts. "
    "Always respond in the same language as the transcript."
)

_USER_PROMPT_TEMPLATE = (
    "From the meeting transcript below, extract:\n"
    "1. 📋 Brief summary (3–5 sentences)\n"
    "2. ✅ Action items with owners (if mentioned)\n"
    "3. 📅 Deadlines and agreements\n\n"
    "Transcript:\n{transcript}"
)

# Reuse a single client across all requests — it manages its own connection pool.
_client: anthropic.AsyncAnthropic | None = None


def _get_client() -> anthropic.AsyncAnthropic:
    global _client
    if _client is None:
        _client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
    return _client


async def analyze(transcript: str) -> str:
    response = await _get_client().messages.create(
        model=CLAUDE_MODEL,
        max_tokens=2048,
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": _USER_PROMPT_TEMPLATE.format(transcript=transcript)}],
    )
    block = response.content[0]
    if not isinstance(block, anthropic.types.TextBlock):
        raise RuntimeError(f"Unexpected response block type from Claude: {type(block)}")
    return block.text
