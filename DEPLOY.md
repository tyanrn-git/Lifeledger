# Деплой на Railway

## 1. Подготовка

1. Аккаунт на [railway.app](https://railway.app)
2. Репозиторий на GitHub (или деплой через Railway CLI)
3. Заполненные секреты: `TELEGRAM_BOT_TOKEN`, `DATABASE_URL`, `OPENAI_API_KEY`

Сгенерируйте секрет webhook:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

## 2. Создание проекта

1. **New Project** → **Deploy from GitHub repo** → выберите LifeLedger
2. Railway соберёт образ по `Dockerfile`

## 3. Переменные окружения

В **Variables** сервиса:

| Переменная | Значение |
|---|---|
| `BOT_MODE` | `webhook` |
| `TELEGRAM_BOT_TOKEN` | токен бота |
| `DATABASE_URL` | строка Supabase PostgreSQL |
| `OPENAI_API_KEY` | ключ OpenAI |
| `WEBHOOK_SECRET` | случайная строка (см. выше) |
| `AI_PROVIDER` | `openai` |
| `DEFAULT_LANGUAGE` | `en` |

`PORT` и `RAILWAY_PUBLIC_DOMAIN` Railway подставит сам.

Опционально вместо `RAILWAY_PUBLIC_DOMAIN`:

```
WEBHOOK_URL=https://<ваш-домен>.up.railway.app/webhook
```

## 4. Публичный домен

1. Сервис → **Settings** → **Networking** → **Generate Domain**
2. Убедитесь, что домен появился в `RAILWAY_PUBLIC_DOMAIN`

## 5. Проверка

- `https://<домен>/health` → `ok`
- Напишите боту в Telegram — должен отвечать
- В логах Railway: `LifeLedger bot started (webhook)`

## 6. Локальная разработка

Оставьте `BOT_MODE=polling` (или не задавайте) и запускайте как раньше:

```bash
python -m app.main
```

Не запускайте polling и webhook с одним токеном одновременно.
