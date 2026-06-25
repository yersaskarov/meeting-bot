import logging

import anthropic

from config import ANTHROPIC_API_KEY, CLAUDE_MODEL

logger = logging.getLogger(__name__)

# Instructions in system prompt so they cannot be overridden by user-supplied transcript content.
_SYSTEM_PROMPT = (
    "You are a meeting analysis assistant. "
    "Extract structured information from meeting transcripts. "
    "Return ONLY a valid JSON object — no markdown, no prose, no code blocks. "
    "Always respond in the same language as the transcript."
)

_USER_PROMPT_TEMPLATE = """\
From the meeting transcript below, extract and return a JSON object with these exact fields:
{{
  "summary": "concise meeting summary in 3-5 sentences",
  "tasks": [{{"owner": "person name or empty string if unknown", "task": "what needs to be done"}}],
  "deadlines": [{{"task": "task description", "date": "deadline date or time"}}],
  "notes": "additional context, recommendations, or observations (empty string if none)"
}}

Return ONLY the JSON. No text before or after. No markdown fences.

Transcript:
{transcript}
"""

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
