# Contributing

Thank you for considering a contribution. Here is everything you need to get started.

## Development setup

```bash
git clone https://github.com/yersaskarov/meeting-bot.git
cd meeting-bot

python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

pip install -r requirements-dev.txt

cp .env.example .env
# Fill in BOT_TOKEN and ANTHROPIC_API_KEY
```

**ffmpeg** is required by Whisper:

| Platform | Command |
|----------|---------|
| macOS | `brew install ffmpeg` |
| Ubuntu/Debian | `sudo apt install ffmpeg` |
| Windows | `winget install Gyan.FFmpeg` |

## Running tests

```bash
pytest
```

All tests mock external services (Whisper, Telegram API, Claude API). No real credentials are needed to run them.

## Code style

This project uses [ruff](https://docs.astral.sh/ruff/) for linting and formatting.

```bash
ruff check .          # lint
ruff format .         # format
mypy config.py analysis.py transcription.py handlers.py main.py  # types
```

CI enforces all three. Your PR will not merge if any of them fail.

## Pull request guidelines

1. Open an issue first for non-trivial changes so we can discuss the approach.
2. Keep PRs focused — one concern per PR.
3. Add or update tests for any behaviour you change.
4. Do not commit `.env`, audio files, or model weights.
5. Use the PR template — fill in all sections.

## Reporting security issues

Do **not** open a public GitHub issue for security vulnerabilities. See [SECURITY.md](SECURITY.md).
