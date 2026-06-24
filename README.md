# 🎙️ Meeting Notes Bot

Telegram-бот, который превращает аудио с митингов в структурированные заметки: транскрибирует речь через Whisper и анализирует содержание через Claude AI.

---

## ✨ Функции

- 🎤 Принимает голосовые сообщения и аудиофайлы (ogg, mp3, wav, m4a)
- 📝 Транскрибирует речь в текст через OpenAI Whisper (локально, без API)
- 🌍 Автоматически определяет язык (русский / английский)
- 🧠 Анализирует транскрипт через Claude AI и выдаёт:
  - 📋 Краткое саммари (3–5 предложений)
  - ✅ Список задач с ответственными
  - 📅 Дедлайны и договорённости
- 🔒 Все аудиофайлы хранятся локально

---

## 🛠️ Стек технологий

| Компонент | Технология |
|-----------|-----------|
| Telegram Bot | [aiogram 3](https://docs.aiogram.dev/) |
| Транскрипция | [OpenAI Whisper](https://github.com/openai/whisper) |
| Анализ текста | [Anthropic Claude API](https://docs.anthropic.com/) |
| Конфигурация | python-dotenv |
| Async I/O | aiofiles |

---

## 🚀 Установка

### 1. Клонируй репозиторий

```bash
git clone https://github.com/your-username/meeting-bot.git
cd meeting-bot
```

### 2. Установи зависимости

```bash
pip install -r requirements.txt
```

> **Примечание:** Whisper тянет PyTorch (~500 MB). Установка займёт 2–5 минут.

### 3. Установи ffmpeg

**Windows (через winget):**
```bash
winget install Gyan.FFmpeg
```

**macOS:**
```bash
brew install ffmpeg
```

**Ubuntu/Debian:**
```bash
sudo apt install ffmpeg
```

### 4. Настрой переменные окружения

Скопируй `.env.example` в `.env` и заполни:

```bash
cp .env.example .env
```

```env
BOT_TOKEN=your_telegram_bot_token_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here
```

### 5. Запусти бота

```bash
python main.py
```

---

## 🔑 Как получить токены

### Telegram Bot Token

1. Открой [@BotFather](https://t.me/BotFather) в Telegram
2. Отправь `/newbot`
3. Следуй инструкциям — получишь токен вида `1234567890:ABC...`

### Anthropic API Key

1. Зарегистрируйся на [console.anthropic.com](https://console.anthropic.com)
2. Перейди в раздел **API Keys**
3. Создай новый ключ — вид `sk-ant-...`

---

## 📁 Структура проекта

```
meeting-bot/
├── main.py           # Точка входа, запуск polling
├── handlers.py       # Обработчики сообщений Telegram
├── transcription.py  # Транскрипция через Whisper
├── analysis.py       # Анализ через Claude API
├── config.py         # Загрузка переменных окружения
├── requirements.txt  # Зависимости
├── .env.example      # Пример конфига
└── audio/            # Сохранённые аудиофайлы (в .gitignore)
```

---

## 💬 Пример работы

```
Пользователь: [отправляет голосовое сообщение 3 минуты]

Бот: ⏳ Транскрибирую аудио...

Бот: 📝 Транскрипт:
Сегодня обсудили запуск нового модуля. Иван возьмёт дизайн до пятницы,
Мария — бэкенд до следующего понедельника. Релиз планируем на 1 июля...

Бот: 🧠 Анализирую...

Бот:
📋 Саммари
Команда обсудила запуск нового модуля. Распределены задачи между
участниками с конкретными дедлайнами. Релиз запланирован на 1 июля.

✅ Задачи
• Иван — дизайн модуля (до пятницы)
• Мария — бэкенд (до следующего понедельника)

📅 Дедлайны и договорённости
• Релиз: 1 июля
• Следующий статус-митинг: обсудить после сдачи бэкенда
```

---

## 🗺️ Планы на будущее

- [ ] Интеграция с Notion — автоматически создавать страницы с заметками
- [ ] Интеграция с Trello / Jira — создавать задачи из списка action items
- [ ] Деплой на сервер (Railway, Fly.io, VPS)
- [ ] Поддержка видеофайлов (MP4, MOV)
- [ ] Сводный дайджест за день/неделю
- [ ] Webhook вместо polling для production

---

---

# 🎙️ Meeting Notes Bot (English)

A Telegram bot that turns meeting audio into structured notes: transcribes speech with Whisper and analyzes content with Claude AI.

---

## ✨ Features

- 🎤 Accepts voice messages and audio files (ogg, mp3, wav, m4a)
- 📝 Transcribes speech locally via OpenAI Whisper (no external API needed)
- 🌍 Auto-detects language (Russian / English)
- 🧠 Analyzes the transcript with Claude AI and returns:
  - 📋 Brief summary (3–5 sentences)
  - ✅ Action items with owners
  - 📅 Deadlines and agreements
- 🔒 All audio files are stored locally

---

## 🚀 Quick Start

```bash
git clone https://github.com/your-username/meeting-bot.git
cd meeting-bot
pip install -r requirements.txt
cp .env.example .env   # fill in BOT_TOKEN and ANTHROPIC_API_KEY
python main.py
```

Install ffmpeg separately — required by Whisper for audio decoding (see platform instructions above).

---

## 🗺️ Roadmap

- [ ] Notion integration — auto-create meeting note pages
- [ ] Trello / Jira integration — push action items as cards/issues
- [ ] Server deployment (Railway, Fly.io, VPS)
- [ ] Video file support (MP4, MOV)
- [ ] Daily/weekly digest
- [ ] Webhook mode for production
