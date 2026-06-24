import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import whisper

logger = logging.getLogger(__name__)

executor = ThreadPoolExecutor(max_workers=1)
_model: whisper.Whisper | None = None


def load_model() -> whisper.Whisper:
    global _model
    if _model is None:
        logger.info("Loading Whisper model...")
        _model = whisper.load_model("base")
        logger.info("Whisper model loaded.")
    return _model


def _run_transcription(file_path: Path) -> str:
    model = load_model()
    result = model.transcribe(str(file_path), task="transcribe")
    return result["text"].strip()


async def transcribe(file_path: Path) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(executor, _run_transcription, file_path)
