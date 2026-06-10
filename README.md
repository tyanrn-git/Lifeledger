# LifeLedger

Telegram-бот для оценки жизненных событий.

## Запуск локально

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m app.main
```

Требуется заполненный `.env` (см. `.env.example`).

## Деплой (Railway)

См. [DEPLOY.md](DEPLOY.md) — webhook, переменные окружения, проверка.

## Документация

- `PRD.md` — продуктовые требования
- `architecture.md` — архитектура
- `database_schema.md` — схема БД
- `telegram_ux.md` — UX-сценарии
