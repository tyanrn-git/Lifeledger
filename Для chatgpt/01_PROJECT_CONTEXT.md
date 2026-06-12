# LifeLedger — текущее состояние проекта

**Версия пакета:** 2026-06-11  
**Последний коммит:** `13b546c` — Fix EventService startup NameError for FeedService type hint  
**Стек:** Python 3.11+, aiogram 3, asyncpg, Supabase PostgreSQL, OpenAI gpt-4o-mini

---

## 1. Что это

Telegram-бот для оценки жизненных событий по шкале **−10…+10**. Пользователь видит чужие события в ленте, ставит оценку или пропускает. Автор добавляет свои события и видит три слоя оценок: самооценка, друзья, сообщество.

Главный экран — **лента оценки**, не меню.

**Прод:** Railway (webhook), домен `lifeledger-production-c53d.up.railway.app`  
**Бот:** @MyLifeledgerbot

---

## 2. Функционал бота (что умеет сейчас)

### 2.1 Команды

| Команда | Действие |
|---------|----------|
| `/start` | Регистрация/обновление профиля → лента оценки. Deep link `?start=invite_<uuid>` — приглашение в друзья |
| `/rate` | Новая или продолженная лента (с intro «подготовлено N событий») |
| `/add` | Мастер добавления события (FSM) |
| `/events` | Список своих событий с оценками |
| `/friends` | Друзья, share-invite, входящие приглашения |
| `/stats` | Статистика автора и оценщика |
| `/settings` | Уведомления и язык событий |
| `/help` | Краткая справка |
| `/cancel` | Отмена мастера `/add` (только в процессе добавления) |

Дополнительно: inline-кнопки на карточке оценки — **Пропустить**, **➕ Add**, **📊 Stats**; после оценки — **Следующее событие**; после батча — **Получить ещё 30**.

### 2.2 Языки

Два независимых слоя:

| Слой | Откуда | Значения | Где используется |
|------|--------|----------|------------------|
| **UI** (`lang`) | `telegram.language_code` | `ru` или `en` | Тексты кнопок, сообщения бота |
| **Контент** (`content_lang`) | `users.language_code` в БД, меняется в `/settings` | 20 языков (en, ru, uk, de, …) | Перевод `normalized_text` в ленте |

Перевод: кэш в `event_translations`; при промахе — AI-перевод и сохранение.

### 2.3 Сценарий: оценщик (лента)

1. `/start` или `/rate` → `FeedService.start_or_resume()`.
2. Если нет событий → сообщение «нет новых» + кнопки Add / Stats.
3. Если новый батч → «Для вас подготовлено {N} событий» (`N` = фактический размер, ≤ 30).
4. Карточка: переведённый текст + шкала **−10…+10** (кнопки) + Skip / Add / Stats. **Тип события не показывается.**
5. После оценки: ваша оценка + **community score** на момент оценки; кнопка «Следующее».
6. Skip → следующее событие в батче без оценки.
7. Конец батча → «Получить ещё 30» (`force_new`) или Add / Stats.

**Правила оценки:**

- Нельзя оценить **своё** событие.
- Одна оценка на пару (user, event); повтор → ошибка.
- Если оценщик — **друг** автора → `rating_scope=friend`, иначе `community`.
- Оценка друзей влияет на `friends_score`, **не** на `community_user_score`.

### 2.4 Сценарий: автор (добавление события)

FSM (`AddEventStates`):

1. Тип: **реальное** или **гипотетическое**.
2. Текст события (свободный ввод).
3. Самооценка −10…+10.
4. AI-анализ (`analyze_event`): язык, normalized text, action, context, category, event time, **ai_score**.
5. Создание в БД; начальный `final_community_score = ai_score`.
6. **Live injection** в активные ленты друзей и других пользователей.
7. Экран «Событие добавлено» с тремя оценками (self / friends / community) + кнопки Rate / My events.

### 2.5 Сценарий: автор (мои события)

- `/events` — список с preview и тремя оценками в строке.
- Детали: тип (реальное/гипотетическое), текст, оценки.
- Удаление с подтверждением → **soft delete**: `is_deleted`, `author_user_id=null`, `anonymized_after_delete=true`. Событие остаётся в БД для статистики сообщества.

### 2.6 Сценарий: друзья

- `/friends`: список имён, счётчик входящих.
- **Share** — `t.me/share/url` с invite deep link.
- **Получить ссылку** — текстовая ссылка в чат.
- **Входящие** — accept/reject с именем пригласившего.
- Переход по ссылке `/start invite_<requester_uuid>`:
  - создаётся `friendships` со статусом `pending`;
  - приглашённый подтверждает или отклоняет;
  - self-invite и повтор — отдельные сообщения об ошибке.

Статусы дружбы: `pending`, `accepted`, `rejected`, `blocked` (enum есть; block UI нет).

### 2.7 Сценарий: статистика (`/stats`)

**Автор** (только события `event_type=real`):

- Три линии: самооценка, друзья, сообщество.
- На каждой: итог + динамика **7 / 30 / 90 дней** (квадратичная формула рейтинга).

**Оценщик:**

- Число оценённых событий.
- Средняя ваша оценка vs средняя community на тех же событиях.
- Отклонение (deviation).

### 2.8 Сценарий: настройки (`/settings`)

- Вкл/выкл push-уведомления (`users.notifications_enabled`).
- Выбор **языка событий** — пагинированный список 20 языков.

### 2.9 Уведомления автору

| Тип | Условие |
|-----|---------|
| `new_ratings` | После оценки события; не чаще 1 раза в час на событие |
| `first_friend_rating` | Первая оценка с `rating_scope=friend` |
| `community_score_changed` | **Не реализовано** (enum в БД есть) |

Отправка через Telegram; запись в таблицу `notifications` (`is_sent`, `sent_at`).

### 2.10 Видимость события в ленте

Событие показывается пользователю, если:

- не удалено (`is_deleted=false`);
- автор ≠ зритель (свои не показываются);
- нет impression у этого пользователя;
- нет impression у этого пользователя на другом событии с тем же `content_hash` (дедуп AI/похожих текстов).

Источники в пуле: **seed** (без автора), **user**, **ai_generated**.

---

## 3. Что реализовано (MVP)

### Фазы architecture.md — статус

| Фаза | Содержание | Статус |
|------|------------|--------|
| 1 | `/start`, регистрация, seed-события, экран оценки | ✅ |
| 2 | `/add`, создание, самооценка, `/events`, удаление | ✅ |
| 3 | Батчи до 30, impressions, оценка, skip, пересчёт | ✅ |
| 4 | AI-анализ, normalized text, ai_score, перевод | ✅ |
| 5 | Invite-ссылка, pending/accept, friend scoring | ✅ |
| 6 | Статистика автора и оценщика, динамика 7/30/90 дн. | ✅ (на лету, без snapshots) |
| 7 | Уведомления + настройки | ⚠️ частично |

### Сверх первоначальной документации

| Фича | Описание |
|------|----------|
| AI-генерация событий | Общий пул `source=ai_generated`, дедуп по `content_hash` на пользователя |
| Приоритет ленты | Друзья → другие пользователи → seed → AI, без shuffle |
| Live injection | Новые события вставляются в **активный** батч зрителя |
| Калибровка AI-оценок | Строгий промпт: большинство событий −2…+2 |
| Scoring audit | Веса AI/users в БД, версия калибровки, фоновый пересчёт |
| Имена друзей | На экране `/friends` и во входящих приглашениях |
| Railway deploy | Webhook, `DEPLOY.md` |

---

## 4. Ключевая логика (как работает сейчас)

### 4.1 Лента и батчи

- Размер батча: `BATCH_SIZE=30` (фактически может быть **меньше**, если в пуле мало событий).
- Пользователь не видит одно событие дважды (таблица `impressions`).
- Приоритет в батче: `source_priority = tier × 10¹² − timestamp_ms` (меньше = раньше).
- **Tiers:** 0 = друзья, 1 = другие users, 2 = seed, 3 = AI.
- **Нет shuffle** (в отличие от PRD/architecture v0).
- При создании события: `FeedService.on_user_event_created()` вставляет его в активные батчи друзей и остальных пользователей.
- При resume/next: `_sync_user_events_into_batch()` подтягивает пропущенные user-события.

**Файлы:** `app/services/feed_service.py`, `app/utils/feed_priority.py`

### 4.2 AI-генерация ленты

- Триггер: доступных событий для пользователя **< `AI_GENERATION_MIN_AVAILABLE` (10)**.
- За раз генерируется **`AI_GENERATION_BATCH_SIZE` (10)** гипотетических событий.
- Общий пул (не per-user), но пользователь не видит дубликаты по `content_hash`.
- Advisory lock `pg_advisory_xact_lock` против гонок.
- **Не догружает до 30** — осознанное решение владельца продукта.

**Файлы:** `app/services/ai_generation_service.py`, `app/db/migrations/007_ai_generated_events.sql`

### 4.3 Community score

Формула:

```
final = ai_score × ai_weight + community_user_score × user_weight
```

Веса по числу community-оценок (`rating_scope='community'`):

| Оценок | AI | Users |
|--------|-----|-------|
| 0 | 100% | 0% |
| 10+ | 90% | 10% |
| 50+ | 80% | 20% |
| 100+ | 50% | 50% |
| 500+ | 20% | 80% |
| 1000+ | 0% | 100% |

`community_user_score` — **только** оценки с `rating_scope='community'` (друзья не входят).

В БД сохраняются: `community_ai_weight`, `community_user_weight`, `scoring_calibration_version` (сейчас **2**).

При старте приложения `ScoreRecalibrationService` пересчитывает breakdown и в фоне обновляет устаревшие `ai_score`.

**Файлы:** `app/utils/scoring.py`, `app/services/score_recalibration_service.py`, `app/db/migrations/008_scoring_audit.sql`

### 4.4 Рейтинг пользователя (статистика)

Не простое среднее. **Signed quadratic sum → корень:**

```python
# Для оценок s1, s2, ...: sum(sign(s) × s²), затем sign × √|sum|
```

**Файл:** `app/utils/rating_math.py`

### 4.5 UI оценщика

- Карточка в ленте: **только текст + приглашение оценить**. Тип события (реальное/гипотетическое) **скрыт**.
- Автор в `/events` видит тип в деталях события.

**Файл:** `app/bot/views.py` — `event_card_text()` vs `event_detail_text()`

### 4.6 AI-промпты

- `SCORING_CALIBRATION` — общий блок для analyze, rescore, generation.
- Температура: generation 0.4, analysis 0.1.
- Модель: gpt-4o-mini (через OpenAI provider).

**Файл:** `app/services/ai/prompts.py`

### 4.7 Уведомления

Реализовано:

- `new_ratings` — debounce 1 час
- `first_friend_rating` — первая оценка от друга
- Вкл/выкл в `/settings`

**Не реализовано:** `community_score_changed` (enum есть в БД, логики нет).

**Файл:** `app/services/notification_service.py`

### 4.8 Друзья

- Приглашение через `t.me/share/url` с deep link.
- Подтверждение addressee.
- Оценки друзей: `rating_scope='friend'`, отдельный `friends_score`.

---

## 5. База данных

**Миграции:** `001` … `008` в `app/db/migrations/`.

| Миграция | Содержание |
|----------|------------|
| 001 | users, events, ratings, event_impressions, rating_batches, 8 seed-событий |
| 002 | дополнительные seed-события |
| 003 | friendships (`pending` / `accepted` / `rejected` / `blocked`) |
| 004 | event_translations |
| 005 | правки seed hypothetical |
| 006 | notifications + enum `notification_type` |
| 007 | `event_source` (seed/user/ai_generated), `content_hash`, `generation_batch_id` |
| 008 | `community_ai_weight`, `community_user_weight`, `scoring_calibration_version` |

**Основные таблицы:**

| Таблица | Назначение |
|---------|------------|
| `users` | Профиль Telegram, `language_code` (контент), `notifications_enabled`, `last_seen_at` |
| `events` | События, scoring, AI-поля, source, content_hash |
| `ratings` | Оценки; unique (event_id, rater_user_id); scope friend/community |
| `event_impressions` | Показ / rated / skipped; привязка к batch; source_priority |
| `rating_batches` | requested_size (30), actual_size, completed_at |
| `friendships` | Друзья с подтверждением |
| `event_translations` | Кэш переводов |
| `notifications` | История уведомлений |

**В schema v0 описано, но нет в БД:**

- `user_rating_snapshots` — статистика считается на лету
- `notification_settings` — флаг на `users.notifications_enabled`

---

## 6. Деплой и runtime

- **Production:** `BOT_MODE=webhook`, aiohttp + aiogram webhook handler.
- **Health:** `GET /health`
- **Не используется:** отдельный FastAPI-слой (в architecture v0 упомянут).
- **AI provider:** только OpenAI (`app/config.py`, factory не поддерживает Anthropic).

См. `DEPLOY.md` в корне репозитория.

---

## 7. Сознательно НЕ делали

| Пункт | Причина |
|-------|---------|
| Догенерация AI до 30 при нехватке событий | Решение владельца: «не надо» |
| Shuffle ленты | Заменён строгим tier-приоритетом |
| Показ типа события оценщику | Скрыто по продуктовому решению |
| Situation archetypes / clustering | Обсуждалось, отложено |
| Admin panel (код) | В разработке; ТЗ — `04_ADMIN_DASHBOARD_SPEC.md` |
| `community_score_changed` notifications | Отложено (~лето 2026) |
| `user_rating_snapshots` | Не нужно для MVP |
| FastAPI как API-слой | aiohttp достаточно |
| Anthropic provider | Только OpenAI в проде |
| pgvector, профили, бейджи | Post-MVP |

---

## 8. Известные ограничения

1. Батч может содержать **27 из 30** (или меньше) — просто нет больше доступных событий.
2. AI генерирует при `<10` доступных, не при `<30`.
3. Событие друга попадёт в ленту только если у зрителя **есть активный батч** или он откроет новую ленту.
4. Старые `ai_score` обновляются фоново при деплое (версия калибровки 2).
5. Документы v0 в корне репо (`PRD.md`, `architecture.md`, …) **устарели** — см. `02_DOCS_DELTA.md`.

---

## 9. Структура репозитория (куда смотреть)

```
app/
  main.py                 # entry, webhook, startup hooks
  config.py
  bot/handlers/           # start, rate, add_event, events, friends, stats, settings, common
  bot/keyboards.py        # inline-клавиатуры
  bot/middlewares.py      # user context, lang / content_lang
  bot/views.py            # тексты UI
  services/
    feed_service.py
    event_service.py
    rating_service.py
    ai_generation_service.py
    score_recalibration_service.py
    notification_service.py
    ai/prompts.py
  utils/
    scoring.py
    feed_priority.py
    rating_math.py
  db/migrations/
  db/repositories/
tests/
```

---

## 10. Тестовые пользователи (прод, для отладки)

| Имя | Telegram | Примечание |
|-----|----------|------------|
| Roman | tyanrn | основной |
| Elena | elena_minho_braga | создавала события для теста ленты |
| Sergey | tyansn | без своих событий |

---

## 11. Открытые направления

- **Admin panel** — ТЗ: `04_ADMIN_DASHBOARD_SPEC.md` (v1.2), Phase A: event log + auth; Phase C2: Event Lifecycle
- Обновить корневые `*.md` в репозитории под текущую реальность
- Archetypes / типовые ситуации для community scoring
- Уведомления `community_score_changed`
