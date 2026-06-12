# Расхождения: документация v0 ↔ реальный код

Используйте эту таблицу при чтении документации v0 в **корне репозитория**: `PRD.md`, `architecture.md`, `database_schema.md`, `telegram_ux.md` (в пакете ChatGPT их нет — только этот delta).

**Легенда статуса:** ✅ реализовано как в доке · ⚠️ частично / иначе · ❌ не сделано · 🔄 намеренно изменено

---

## Продукт и UX

| Документ | Было в v0 | Сейчас в коде | Статус |
|----------|-----------|---------------|--------|
| PRD, UX | Главный экран — лента оценки | Так же | ✅ |
| PRD, UX | На карточке оценщика виден тип (реальное/гипотетическое) | Тип **скрыт** у оценщика; автор видит в `/events` | 🔄 |
| PRD | Подборка всегда 30 событий | До 30, фактически может быть меньше | ⚠️ |
| telegram_ux | Анонимность автора | Так же | ✅ |
| PRD | Три оценки: self, friends, community | Так же | ✅ |
| — | Имена друзей на `/friends` | Показываются имена и входящие инвайты | ✅ (нет в v0) |
| — | Два слоя языка: UI (ru/en) и контент (20 языков) | UI от Telegram; контент в `/settings` | ✅ (слабо в v0) |
| — | Статистика автора | Только **реальные** события; гипотетические не входят | ⚠️ |
| — | `/help` | Реализована краткая справка | ✅ |

---

## Лента и батчи

| Документ | Было в v0 | Сейчас в коде | Статус |
|----------|-----------|---------------|--------|
| architecture §10 | Shuffle внутри приоритетов | **Нет shuffle**, строгий порядок по tier + время | 🔄 |
| architecture §10 | 3 приоритета: мало оценок, друзья, остальное | 4 tier: друзья → users → seed → AI | 🔄 |
| architecture §10 | Boost «мало community-оценок» | `under_rated_threshold` в SQL выборке, но главный порядок — tier | ⚠️ |
| — | События друзей только в новом батче | **Live injection** в активный батч + sync при resume | ✅ (нет в v0) |
| — | AI-события при нехватке пула | Генерация при `<10` доступных, batch 10 шт. | ✅ (нет в v0) |
| — | Догрузка AI до 30 | **Не делаем** (решение владельца) | 🔄 |

---

## Scoring и AI

| Документ | Было в v0 | Сейчас в коде | Статус |
|----------|-----------|---------------|--------|
| architecture | AI score без жёсткой калибровки | `SCORING_CALIBRATION` в промптах, версия 2 | 🔄 |
| architecture | Community = blend AI + users | Так же, пороги в `scoring.py` | ✅ |
| — | Friend ratings в community avg | **Исправлено:** только `rating_scope='community'` | 🔄 |
| — | Веса scoring в БД | `community_ai_weight`, `community_user_weight`, `scoring_calibration_version` | ✅ (нет в v0 schema) |
| — | Пересчёт ai_score при деплое | `ScoreRecalibrationService` на startup | ✅ (нет в v0) |
| architecture | Среднее для рейтинга пользователя | **Quadratic signed sum → √** (`rating_math.py`) | 🔄 |

---

## Друзья и уведомления

| Документ | Было в v0 | Сейчас в коде | Статус |
|----------|-----------|---------------|--------|
| PRD | Invite + подтверждение | Share link `t.me/share/url` | ✅ |
| PRD, schema | `community_score_changed` | Enum в БД, **логики нет** | ❌ |
| PRD | `new_ratings`, `first_friend_rating` | Реализованы с debounce | ✅ |
| PRD | Настройки уведомлений | `/settings` toggle | ✅ |

---

## Инфраструктура и архитектура

| Документ | Было в v0 | Сейчас в коде | Статус |
|----------|-----------|---------------|--------|
| architecture | FastAPI для webhook/health | **aiohttp** webhook + `/health` | 🔄 |
| architecture | OpenAI или Claude | Только **OpenAI** в factory | ⚠️ |
| architecture | Render / Railway / Fly | **Railway** в проде | ✅ |
| architecture | Background jobs — опционально | Async tasks: AI rescore на startup | ⚠️ |
| database_schema | `user_rating_snapshots` | Таблицы **нет** | ❌ |
| database_schema | `events.source` | Добавлено в migration 007 | ✅ |
| — | Admin panel | Web Admin v1: dashboard, users, events, lifecycle, analytics, export, **Activity log** | ✅ |
| — | Situation archetypes | Не реализованы | ❌ |
| — | pgvector, clustering | Post-MVP | ❌ |

---

## Миграции vs database_schema.md

| В schema v0 | В реальных миграциях |
|-------------|---------------------|
| Базовые таблицы 001 | ✅ |
| friendships 003 | ✅ |
| event_translations 004 | ✅ |
| notifications 006 | ✅ |
| — | 007: ai_generated, content_hash |
| — | 008: scoring audit columns |
| user_rating_snapshots | ❌ отсутствует |

---

## Быстрая шпаргалка для ChatGPT

**Если в PRD/architecture написано одно, а здесь другое — верь этому файлу и `01_PROJECT_CONTEXT.md`.**

Частые ловушки:

1. Не предлагать shuffle ленты.
2. Не предлагать показывать тип события оценщику (если не попросят явно вернуть).
3. Не предлагать автодогрузку AI до 30.
4. Не считать `database_schema.md` полной схемой — смотреть миграции 007–008 в `app/db/migrations/`.
5. `community_score_changed` — в планах, не в коде.
