🇬🇧 English version: [../README.md](../README.md)

# Meeting Notes Bot

[![CI](https://github.com/yersaskarov/meeting-bot/actions/workflows/ci.yml/badge.svg)](https://github.com/yersaskarov/meeting-bot/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](../LICENSE)
[![Code style: ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

Telegram-бот, который превращает запись встречи в структурированные заметки. Расшифровывает речь локально через [OpenAI Whisper](https://github.com/openai/whisper) — без сторонних API для транскрипции — и выделяет саммари, задачи и дедлайны с помощью [Claude](https://docs.anthropic.com/).

> **Язык ответов бота:** русский или английский — определяется автоматически по языку аудио.

---

## Возможности

- Принимает голосовые сообщения и аудиофайлы (ogg, mp3, wav, m4a, mp4, flac, opus)
- Транскрибирует речь **локально** — аудио не покидает ваш сервер
- Автоматически определяет язык (русский / английский; при низкой уверенности — русский)
- Анализирует транскрипт через Claude AI и возвращает:
  - Краткое саммари (3–5 предложений)
  - Список задач с ответственными
  - Дедлайны и договорённости
- Сохраняет историю встреч в SQLite и позволяет открыть последние заметки через `/history`
- Ограничения: 25 МБ на файл, 30 минут длительности, 5 минут на транскрипцию
- Грамотная обработка всех сбоев Claude API: лимиты, ошибки авторизации, перегрузка

---

## Архитектура

```
Пользователь Telegram
        │
        │  голосовое / аудиофайл
        ▼
┌─────────────┐
│  handlers.py │  проверка размера, длительности, расширения
│  (aiogram 3) │
└──────┬───────┘
       │ сохраняет файл в audio/
       ▼
┌──────────────────┐
│ transcription.py  │  ThreadPoolExecutor(max_workers=1)
│ (Whisper — локал) │  определение языка → транскрипция
└──────┬────────────┘
       │ текст транскрипта
       ▼
┌──────────────┐
│ analysis.py   │  AsyncAnthropic (singleton-клиент)
│ (Claude API)  │  system prompt + транскрипт пользователя
└──────┬────────┘
       │ структурированные заметки
       ▼
┌────────────┐
│ storage.py │  SQLite-хранилище для /history
└────────────┘
       │
       ▼
Пользователь Telegram
```

Whisper работает в `ThreadPoolExecutor`, чтобы CPU-нагрузка транскрипции не блокировала асинхронный event loop. Клиент Anthropic — модульный singleton, переиспользующий внутренний пул соединений между запросами.

---

## Быстрый старт (Docker — рекомендуется)

```bash
git clone https://github.com/yersaskarov/meeting-bot.git
cd meeting-bot

cp .env.example .env
# Заполни BOT_TOKEN и ANTHROPIC_API_KEY

docker compose up --build
```

При сборке образ заранее скачивает модель Whisper — контейнер стартует мгновенно.

---

## Ручная установка

**Требования:** Python 3.11+, ffmpeg

```bash
# 1. Клонируй репозиторий
git clone https://github.com/yersaskarov/meeting-bot.git
cd meeting-bot

# 2. Виртуальное окружение
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 3. Зависимости
pip install -r requirements.txt

# 4. ffmpeg (нужен Whisper для декодирования аудио)
# macOS:          brew install ffmpeg
# Ubuntu/Debian:  sudo apt install ffmpeg
# Windows:        winget install Gyan.FFmpeg

# 5. Конфигурация
cp .env.example .env
# Открой .env и укажи BOT_TOKEN и ANTHROPIC_API_KEY

# 6. Запуск
python main.py
```

> При первой установке Whisper подтянет PyTorch (~500 МБ). Это ожидаемое поведение.

---

## Конфигурация

Все настройки задаются через переменные окружения (файл `.env` или системное окружение).

| Переменная | Обязательна | Значение по умолчанию | Описание |
|---|---|---|---|
| `BOT_TOKEN` | Да | — | Токен Telegram-бота от [@BotFather](https://t.me/BotFather) |
| `ANTHROPIC_API_KEY` | Да | — | Ключ Claude API из [console.anthropic.com](https://console.anthropic.com) |
| `WHISPER_MODEL` | Нет | `small` | Размер модели Whisper: `tiny`, `base`, `small`, `medium`, `large` |
| `CLAUDE_MODEL` | Нет | `claude-sonnet-4-6` | Идентификатор модели Claude |
| `DB_PATH` | Нет | `data/meetings.db` | Путь к SQLite-базе истории встреч |

### Где получить токены

**Токен Telegram-бота**
1. Открой [@BotFather](https://t.me/BotFather)
2. Отправь `/newbot` и следуй инструкциям
3. Скопируй токен в формате `1234567890:ABC...`

**Ключ Anthropic API**
1. Войди на [console.anthropic.com](https://console.anthropic.com)
2. Перейди в раздел **API Keys** → **Create Key**
3. Скопируй ключ в формате `sk-ant-...`

---

## Структура проекта

```
meeting-bot/
├── main.py              # Точка входа — настройка логирования, polling
├── handlers.py          # Обработчики сообщений, валидация, оркестрация
├── transcription.py     # Транскрипция через Whisper (thread pool)
├── analysis.py          # Вызов Claude API (singleton-клиент)
├── formatter.py         # Парсинг JSON от Claude и форматирование сообщений
├── storage.py           # SQLite-хранилище истории встреч
├── config.py            # Загрузка переменных окружения
├── requirements.txt     # Runtime-зависимости
├── requirements-dev.txt # Зависимости для разработки и тестов
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml       # Конфигурация ruff, mypy, pytest
└── tests/
    ├── test_analysis.py
    ├── test_formatter.py
    ├── test_handlers.py
    ├── test_storage.py
    ├── test_transcription.py
    └── test_pipeline.py  # Интеграционные тесты всего пайплайна
```

---

## Запуск тестов

```bash
pip install -r requirements-dev.txt
pytest
```

Все тесты мокируют внешние сервисы. Реальные ключи API и аудиофайлы не нужны.

```bash
ruff check .          # линтинг
ruff format --check . # проверка форматирования
mypy .                # проверка типов
```

---

## Решение проблем

**`ffmpeg not found` / Whisper падает при запуске**
Установи ffmpeg для своей платформы (см. раздел «Ручная установка»). Whisper требует его для декодирования аудио.

**Бот запустился, но не отвечает**
- Проверь корректность `BOT_TOKEN`: `curl https://api.telegram.org/bot<TOKEN>/getMe`
- Посмотри `errors.log` на наличие ошибок при старте.

**Транскрипция зависает или превышает таймаут**
- По умолчанию используется модель `small`. Попробуй `WHISPER_MODEL=base` — она быстрее, но менее точная.
- Убедись, что сервер располагает достаточным объёмом RAM: `small` требует ~500 МБ, `medium` — ~1,5 ГБ.

**`AuthenticationError` от Claude**
`ANTHROPIC_API_KEY` недействителен или истёк. Создай новый на [console.anthropic.com](https://console.anthropic.com).

**`RateLimitError` от Claude**
Превышен лимит запросов к Claude API. Проверь текущее потребление на [console.anthropic.com](https://console.anthropic.com).

**Аудио транскрибируется, но язык определяется неверно**
Используй `WHISPER_MODEL=medium` или `large` — они лучше справляются с зашумлённым и смешанноязычным аудио.

---

## Дорожная карта

- [ ] Webhook-режим для production-развёртывания
- [ ] Поддержка видеофайлов (MP4, MOV) — извлечение аудиодорожки перед транскрипцией
- [ ] Интеграция с Notion — автоматическое создание страниц с заметками
- [ ] Интеграция с Jira / Linear — создание задач из action items
- [ ] Ежедневный / еженедельный дайджест встреч

---

## Участие в разработке

См. [CONTRIBUTING.md](../CONTRIBUTING.md).

---

## Лицензия

[MIT](../LICENSE) © 2026 Yersultan Askarov
