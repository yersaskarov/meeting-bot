import os

from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN: str | None = os.getenv("BOT_TOKEN")
ANTHROPIC_API_KEY: str | None = os.getenv("ANTHROPIC_API_KEY")
WHISPER_MODEL: str = os.getenv("WHISPER_MODEL", "small")
CLAUDE_MODEL: str = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")
