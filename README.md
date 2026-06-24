🇷🇺 Russian version: [docs/README_RU.md](docs/README_RU.md)

# Meeting Notes Bot

[![CI](https://github.com/yersaskarov/meeting-bot/actions/workflows/ci.yml/badge.svg)](https://github.com/yersaskarov/meeting-bot/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Code style: ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

A Telegram bot that turns meeting audio into structured notes. It transcribes speech locally with [OpenAI Whisper](https://github.com/openai/whisper) (no external transcription API) and extracts summaries, action items, and deadlines with [Claude](https://docs.anthropic.com/).

> **Bot language:** The bot sends messages in Russian and English depending on the detected audio language.

---

## Features

- Accepts voice messages and audio files (ogg, mp3, wav, m4a, mp4, flac, opus)
- Transcribes speech **locally** — no audio ever leaves your server
- Auto-detects language (Russian / English; falls back to Russian on low confidence)
- Extracts via Claude AI:
  - Brief summary (3–5 sentences)
  - Action items with owners
  - Deadlines and agreements
- File guards: 25 MB size limit, 30-minute duration limit, 5-minute transcription timeout
- Graceful error handling for every Claude API failure mode (rate limits, auth errors, overload)

---

## Architecture

```
Telegram User
     │
     │  voice / audio file
     ▼
┌─────────────┐
│  handlers.py │  validates size, duration, extension
│  (aiogram 3) │
└──────┬───────┘
       │ downloads file to audio/
       ▼
┌──────────────────┐
│ transcription.py  │  ThreadPoolExecutor(max_workers=1)
│ (Whisper — local) │  detect language → transcribe
└──────┬────────────┘
       │ plain text transcript
       ▼
┌──────────────┐
│ analysis.py   │  AsyncAnthropic (singleton client)
│ (Claude API)  │  system prompt + user transcript
└──────┬────────┘
       │ structured notes
       ▼
Telegram User
```

Whisper runs in a `ThreadPoolExecutor` so CPU-bound transcription never blocks the async event loop. The Anthropic client is a module-level singleton that reuses its internal connection pool across requests.

---

## Quick start (Docker — recommended)

```bash
git clone https://github.com/yersaskarov/meeting-bot.git
cd meeting-bot

cp .env.example .env
# Fill in BOT_TOKEN and ANTHROPIC_API_KEY

docker compose up --build
```

The image pre-downloads the Whisper model during build so the container starts instantly.

---

## Manual setup

**Requirements:** Python 3.11+, ffmpeg

```bash
# 1. Clone
git clone https://github.com/yersaskarov/meeting-bot.git
cd meeting-bot

# 2. Virtual environment
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 3. Dependencies
pip install -r requirements.txt

# 4. ffmpeg (required by Whisper)
# macOS:         brew install ffmpeg
# Ubuntu/Debian: sudo apt install ffmpeg
# Windows:       winget install Gyan.FFmpeg

# 5. Configuration
cp .env.example .env
# Edit .env and set BOT_TOKEN and ANTHROPIC_API_KEY

# 6. Run
python main.py
```

> Whisper pulls PyTorch (~500 MB) on first install. This is expected.

---

## Configuration

All configuration is via environment variables (`.env` file or system environment).

| Variable | Required | Default | Description |
|---|---|---|---|
| `BOT_TOKEN` | Yes | — | Telegram bot token from [@BotFather](https://t.me/BotFather) |
| `ANTHROPIC_API_KEY` | Yes | — | Claude API key from [console.anthropic.com](https://console.anthropic.com) |
| `WHISPER_MODEL` | No | `small` | Whisper model size: `tiny`, `base`, `small`, `medium`, `large` |
| `CLAUDE_MODEL` | No | `claude-sonnet-4-6` | Claude model ID |

### Getting credentials

**Telegram Bot Token**
1. Open [@BotFather](https://t.me/BotFather)
2. Send `/newbot` and follow the prompts
3. Copy the token (format: `1234567890:ABC...`)

**Anthropic API Key**
1. Sign in at [console.anthropic.com](https://console.anthropic.com)
2. Go to **API Keys** → **Create Key**
3. Copy the key (format: `sk-ant-...`)

---

## Project structure

```
meeting-bot/
├── main.py              # Entry point — logging setup, polling loop
├── handlers.py          # Telegram message handlers, validation, orchestration
├── transcription.py     # Whisper transcription (thread pool)
├── analysis.py          # Claude API call (singleton client)
├── config.py            # Environment variable loading
├── requirements.txt     # Runtime dependencies
├── requirements-dev.txt # Dev/test dependencies
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml       # ruff, mypy, pytest config
└── tests/
    ├── test_analysis.py
    ├── test_handlers.py
    ├── test_transcription.py
    └── test_pipeline.py  # End-to-end pipeline integration tests
```

---

## Running tests

```bash
pip install -r requirements-dev.txt
pytest
```

All tests mock external services. No real API keys or audio files needed.

```bash
ruff check .          # lint
ruff format --check . # format check
mypy config.py analysis.py transcription.py handlers.py main.py
```

---

## Troubleshooting

**`ffmpeg not found` / Whisper crashes immediately**
Install ffmpeg for your platform (see Manual Setup above). Whisper requires it to decode audio.

**Bot starts but never responds**
- Confirm `BOT_TOKEN` is correct. Test with `curl https://api.telegram.org/bot<TOKEN>/getMe`.
- Check `errors.log` for startup errors.

**Transcription takes forever or times out**
- The `small` model is the default. Use `WHISPER_MODEL=base` for faster (less accurate) transcription.
- Ensure the server has enough RAM. The `small` model needs ~500 MB, `medium` ~1.5 GB.

**`AuthenticationError` from Claude**
The `ANTHROPIC_API_KEY` is invalid or expired. Generate a new one at [console.anthropic.com](https://console.anthropic.com).

**`RateLimitError` from Claude**
You've exceeded your Claude API rate limit. Check your usage at [console.anthropic.com](https://console.anthropic.com).

**Audio is transcribed but language is wrong**
Set `WHISPER_MODEL=medium` or `large` for better language detection on noisy or mixed-language audio.

---

## Roadmap

- [ ] Webhook mode for production deployments
- [ ] Support for video files (MP4, MOV) — extract audio track before transcription
- [ ] Notion integration — auto-create meeting note pages
- [ ] Jira / Linear integration — push action items as tickets
- [ ] Daily/weekly digest of meeting summaries

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

---

## License

[MIT](LICENSE) © 2026 Yersultan Askarov
