"""Unit tests for transcription.py (Whisper)."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import transcription


@pytest.fixture(autouse=True)
def reset_model():
    """Reset the global Whisper model before each test."""
    transcription._model = None
    yield
    transcription._model = None


# ---------------------------------------------------------------------------
# load_model
# ---------------------------------------------------------------------------


def test_load_model_uses_configured_model():
    """load_model must pass WHISPER_MODEL and WHISPER_CACHE to whisper.load_model."""
    mock_model = MagicMock()
    with (
        patch("transcription.whisper.load_model", return_value=mock_model) as mock_load,
        patch("transcription.WHISPER_MODEL", "small"),
        patch("transcription.WHISPER_CACHE", "/app/.cache/whisper"),
    ):
        result = transcription.load_model()

    mock_load.assert_called_once_with("small", download_root="/app/.cache/whisper")
    assert result is mock_model


def test_load_model_only_once():
    """Calling load_model multiple times must load the model exactly once."""
    mock_model = MagicMock()
    with patch("transcription.whisper.load_model", return_value=mock_model) as mock_load:
        transcription.load_model()
        transcription.load_model()
        transcription.load_model()

    assert mock_load.call_count == 1


# ---------------------------------------------------------------------------
# _detect_language
# ---------------------------------------------------------------------------


def _make_model(probs: dict) -> MagicMock:
    model = MagicMock()
    model.dims.n_mels = 80
    model.device = "cpu"
    model.detect_language.return_value = (None, probs)
    return model


def _call_detect(model, path="test.ogg"):
    with (
        patch("transcription.whisper.load_audio"),
        patch("transcription.whisper.pad_or_trim"),
        patch("transcription.whisper.log_mel_spectrogram") as mock_mel,
    ):
        mock_mel.return_value.to.return_value = MagicMock()
        return transcription._detect_language(model, Path(path))


def test_detect_language_high_confidence_uses_detected():
    """When confidence >= 0.8 the detected language is returned."""
    model = _make_model({"en": 0.92, "ru": 0.05, "fr": 0.03})
    assert _call_detect(model) == "en"


def test_detect_language_russian_high_confidence():
    """Russian detected with high confidence returns 'ru'."""
    model = _make_model({"ru": 0.85, "en": 0.10, "uk": 0.05})
    assert _call_detect(model) == "ru"


def test_detect_language_low_confidence_falls_back_to_russian():
    """When max confidence < 0.8, fallback to Russian."""
    model = _make_model({"kk": 0.45, "ru": 0.30, "en": 0.25})
    assert _call_detect(model) == "ru"


def test_detect_language_boundary_exactly_08():
    """Confidence exactly 0.8 should use the detected language (>= 0.8)."""
    model = _make_model({"de": 0.80, "ru": 0.20})
    assert _call_detect(model) == "de"


# ---------------------------------------------------------------------------
# transcribe (async)
# ---------------------------------------------------------------------------


async def test_transcribe_success():
    """Successful transcription returns the text from _run_transcription."""
    with patch("transcription._run_transcription", return_value="Привет мир"):
        result = await transcription.transcribe(Path("test.ogg"))
    assert result == "Привет мир"


async def test_transcribe_corrupted_file_raises():
    """A corrupted file causes _run_transcription to raise; the exception propagates."""
    with (
        patch("transcription._run_transcription", side_effect=RuntimeError("decode error")),
        pytest.raises(RuntimeError, match="decode error"),
    ):
        await transcription.transcribe(Path("corrupt.ogg"))


# ---------------------------------------------------------------------------
# check_ffmpeg
# ---------------------------------------------------------------------------


def test_check_ffmpeg_raises_when_not_found():
    """check_ffmpeg must raise RuntimeError with install instructions when ffmpeg is absent."""
    with (
        patch("transcription.shutil.which", return_value=None),
        pytest.raises(RuntimeError, match="ffmpeg not found"),
    ):
        transcription.check_ffmpeg()


def test_check_ffmpeg_passes_when_found():
    """check_ffmpeg must not raise when ffmpeg is present in PATH."""
    with patch("transcription.shutil.which", return_value="/usr/bin/ffmpeg"):
        transcription.check_ffmpeg()  # must not raise
