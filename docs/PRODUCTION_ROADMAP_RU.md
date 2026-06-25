# Production Roadmap — Meeting Notes Bot

Этот документ описывает шаги для перевода бота в production на VPS.
Текущий статус: **подготовлен к деплою** (все Critical/High issues закрыты).

---

## Этап 1 — VPS и базовая настройка

**Цель:** сервер готов к запуску Docker-контейнера.

### 1.1 Выбор сервера

- Минимум: 2 vCPU, 4 GB RAM, 20 GB SSD
- Рекомендация: Hetzner CX22 / DigitalOcean Droplet 4GB / Timeweb Cloud
- ОС: Ubuntu 24.04 LTS

### 1.2 Ubuntu hardening

```bash
# Обновление системы
apt update && apt upgrade -y

# Создание non-root пользователя
adduser deploy
usermod -aG sudo deploy

# Настройка SSH — только ключи, запрет root login
# /etc/ssh/sshd_config:
#   PermitRootLogin no
#   PasswordAuthentication no
#   PubkeyAuthentication yes

# Firewall
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw enable

# Fail2ban против брутфорса
apt install fail2ban -y
```

### 1.3 Установка Docker

```bash
# Официальная установка Docker на Ubuntu
curl -fsSL https://get.docker.com | sh
usermod -aG docker deploy
```

---

## Этап 2 — Docker Deployment

**Цель:** бот запущен в Docker, данные персистентны.

### 2.1 Подготовка директорий на хосте

```bash
# Создать директории ДО запуска docker compose
mkdir -p /opt/meeting-bot/data /opt/meeting-bot/logs /opt/meeting-bot/audio

# Установить правильный владелец (UID 1001 = botuser внутри контейнера)
chown -R 1001:1001 /opt/meeting-bot/data /opt/meeting-bot/logs
```

> ⚠️ Этот шаг важен: без него Docker создаст директории от root,
> и `botuser` (uid 1001) не сможет писать в них.

### 2.2 Настройка .env

```bash
cp .env.example .env
nano .env  # прописать BOT_TOKEN и ANTHROPIC_API_KEY
```

### 2.3 Запуск

```bash
cd /opt/meeting-bot
docker compose up -d --build
docker compose logs -f
```

### 2.4 Проверка healthcheck

```bash
# Статус контейнера (healthy/unhealthy/starting)
docker ps

# Детали healthcheck
docker inspect meeting-bot_bot_1 | jq '.[0].State.Health'
```

---

## Этап 3 — Домен и HTTPS

**Цель:** бот доступен по HTTPS (требование Telegram Webhook API).

### 3.1 Домен

- Купить домен или использовать бесплатный (freenom, DuckDNS)
- Прописать A-запись → IP VPS

### 3.2 Nginx reverse proxy

Установка:
```bash
apt install nginx -y
```

Конфиг `/etc/nginx/sites-available/meeting-bot`:
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        return 301 https://$host$request_uri;
    }
}

server {
    listen 443 ssl;
    server_name your-domain.com;

    ssl_certificate     /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

    location /webhook/ {
        proxy_pass http://127.0.0.1:8080/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 3.3 HTTPS через Let's Encrypt

```bash
apt install certbot python3-certbot-nginx -y
certbot --nginx -d your-domain.com
# Автообновление сертификата — добавляется в cron автоматически
```

---

## Этап 4 — Telegram Webhook (вместо Polling)

**Цель:** переход с polling на webhook для production.

### Почему webhook лучше polling в production

| | Polling | Webhook |
|---|---|---|
| Latency | ~1s | мгновенно |
| Нагрузка на сервер | Постоянные запросы | Только при событии |
| VPS-ready | Нет (нет HTTPS) | Да |
| Локальная разработка | Да | Нет (нужен HTTPS) |

### Изменения в коде

В `main.py` заменить `dp.start_polling(bot)` на:

```python
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

WEBHOOK_PATH = "/webhook/{token}"
WEBHOOK_URL = f"https://your-domain.com{WEBHOOK_PATH}"

async def main():
    ...
    await bot.set_webhook(WEBHOOK_URL.format(token=BOT_TOKEN))

    app = web.Application()
    SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path=WEBHOOK_PATH)
    setup_application(app, dp, bot=bot)
    web.run_app(app, host="0.0.0.0", port=8080)
```

Добавить `aiohttp` в `requirements.txt`.

В `docker-compose.yml` открыть порт:
```yaml
ports:
  - "127.0.0.1:8080:8080"
```

---

## Этап 5 — Логи и мониторинг

**Цель:** видеть состояние бота и получать алерты.

### 5.1 Просмотр логов

```bash
# Текущие логи контейнера
docker compose logs -f bot

# Ошибки из файла
tail -f /opt/meeting-bot/logs/errors.log
```

### 5.2 Logrotate для файловых логов

`/etc/logrotate.d/meeting-bot`:
```
/opt/meeting-bot/logs/errors.log {
    daily
    rotate 14
    compress
    delaycompress
    missingok
    notifempty
}
```

### 5.3 Мониторинг (упрощённый)

- **Uptime Robot** (бесплатно): мониторит доступность домена
- **Telegram alert**: при падении контейнера Docker отправляет сообщение через отдельный бот
- В будущем: Prometheus + Grafana или Datadog

### 5.4 Алерт при падении контейнера (systemd + docker)

Создать systemd unit `/etc/systemd/system/meeting-bot.service`:
```ini
[Unit]
Description=Meeting Notes Bot
After=docker.service
Requires=docker.service

[Service]
WorkingDirectory=/opt/meeting-bot
ExecStart=/usr/bin/docker compose up
ExecStop=/usr/bin/docker compose down
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
systemctl enable meeting-bot
systemctl start meeting-bot
```

---

## Этап 6 — Backup SQLite

**Цель:** данные встреч не потеряются при сбое.

### 6.1 Ручной бэкап

```bash
# Безопасный бэкап SQLite (без блокировки)
sqlite3 /opt/meeting-bot/data/meetings.db ".backup /opt/meeting-bot/backups/meetings_$(date +%Y%m%d).db"
```

### 6.2 Автоматический бэкап (cron)

```bash
# /etc/cron.d/meeting-bot-backup
0 3 * * * root sqlite3 /opt/meeting-bot/data/meetings.db \
  ".backup /opt/meeting-bot/backups/meetings_$(date +\%Y\%m\%d).db" && \
  find /opt/meeting-bot/backups -name "*.db" -mtime +30 -delete
```

### 6.3 Offsite бэкап

В будущем: rclone → S3 / Backblaze B2 / Google Drive.

---

## Этап 7 — GitHub Actions Auto Deploy

**Цель:** при push в main — автоматический деплой на VPS.

### 7.1 SSH ключ для деплоя

```bash
# На VPS
ssh-keygen -t ed25519 -f ~/.ssh/deploy_key -N ""
cat ~/.ssh/deploy_key.pub >> ~/.ssh/authorized_keys
```

В GitHub → Settings → Secrets:
- `VPS_HOST` — IP сервера
- `VPS_USER` — deploy
- `VPS_SSH_KEY` — содержимое `~/.ssh/deploy_key` (приватный ключ)

### 7.2 Добавить job в ci.yml

```yaml
  deploy:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'
    steps:
      - name: Deploy to VPS
        uses: appleboy/ssh-action@v1
        with:
          host: ${{ secrets.VPS_HOST }}
          username: ${{ secrets.VPS_USER }}
          key: ${{ secrets.VPS_SSH_KEY }}
          script: |
            cd /opt/meeting-bot
            git pull origin main
            docker compose up -d --build
            docker compose ps
```

---

## Этап 8 — Улучшения Medium/Low (после v1.0)

### Resource limits в docker-compose.yml

```yaml
services:
  bot:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
        reservations:
          memory: 1G
```

### Network isolation

```yaml
services:
  bot:
    networks:
      - internal

networks:
  internal:
    driver: bridge
    internal: true
```

### Rate limiting per user

В `handlers.py` добавить простой in-memory rate limiter:
```python
from collections import defaultdict
import time

_last_request: dict[int, float] = defaultdict(float)
RATE_LIMIT_SECONDS = 30

def _is_rate_limited(user_id: int) -> bool:
    now = time.time()
    if now - _last_request[user_id] < RATE_LIMIT_SECONDS:
        return True
    _last_request[user_id] = now
    return False
```

### SQLite миграции (Alembic или ручные)

При изменении схемы — создавать миграционные скрипты:
```
migrations/
  001_initial.sql
  002_add_language_column.sql
```

### Structured logging (JSON)

```python
import json
import logging

class JsonFormatter(logging.Formatter):
    def format(self, record):
        return json.dumps({
            "time": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        })
```

---

## Чеклист до Release v1.0

- [ ] VPS арендован и настроен (Ubuntu 24.04)
- [ ] Docker установлен, пользователь добавлен в группу docker
- [ ] Директории `data/`, `logs/` созданы с правильным UID
- [ ] `.env` заполнен с реальными ключами
- [ ] `docker compose up -d --build` — успешно
- [ ] `docker ps` → статус `healthy`
- [ ] Домен настроен, A-запись указывает на IP
- [ ] HTTPS сертификат получен (certbot)
- [ ] Nginx настроен как reverse proxy
- [ ] Webhook подключён и проверен
- [ ] Бот отвечает на голосовые сообщения
- [ ] `/history` работает, данные сохраняются после перезапуска
- [ ] Логи пишутся в `logs/errors.log`
- [ ] Cron для backup настроен
- [ ] GitHub Actions CD pipeline настроен
- [ ] Мониторинг (Uptime Robot) настроен
