import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import whisper

from config import WHISPER_MODEL

logger = logging.getLogger(__name__)

executor = ThreadPoolExecutor(max_workers=1)
_model: whisper.Whisper | None = None


def load_model() -> whisper.Whisper:
    global _model
    if _model is None:
        logger.info("Loading Whisper model '%s'...", WHISPER_MODEL)
        _model = whisper.load_model(WHISPER_MODEL)
        logger.info("Whisper model loaded.")
    return _model


def _detect_language(model: whisper.Whisper, file_path: Path) -> str:
    audio = whisper.load_audio(str(file_path))
    audio = whisper.pad_or_trim(audio)
    mel = whisper.log_mel_spectrogram(audio, n_mels=model.dims.n_mels).to(model.device)
    _, probs = model.detect_language(mel)
    detected = max(probs, key=probs.get)
    confidence = probs[detected]
    if confidence >= 0.8:
        logger.info("Language detected: %s (confidence: %.2f)", detected, confidence)
        return detected
    logger.info("Low confidence %.2f for '%s', defaulting to Russian", confidence, detected)
    return "ru"


def _run_transcription(file_path: Path) -> str:
    model = load_model()
    language = _detect_language(model, file_path)
    result = model.transcribe(str(file_path), language=language, task="transcribe")
    return result["text"].strip()


async def transcribe(file_path: Path) -> str:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(executor, _run_transcription, file_path)
