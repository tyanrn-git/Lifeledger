# LifeLedger — ТЗ на Web Admin Dashboard

**Версия:** 1.2  
**Дата:** 2026-06-11  
**Статус:** Утверждено к разработке (живой документ — обновлять по мере уточнений)  
**Основа:** production MVP (Railway, aiogram, aiohttp, Supabase PostgreSQL, OpenAI)

> **Как вести этот документ:** при каждом уточнении в разработке добавляйте запись в [Changelog](#changelog) и правьте соответствующий раздел. Не создавайте параллельных версий ТЗ.  
> **План работ:** `05_ADMIN_IMPLEMENTATION_PLAN.md` — порядок спринтов, файлы, чеклисты.

---

## 1. Цели админки

1. **Продуктовая аналитика** — воронки, retention, где отваливаются пользователи.
2. **Аналитика пользователей** — профиль, путь, активность.
3. **Аналитика событий** — контент, scoring, источники, **жизненный цикл события**.
4. **Аналитика ленты** — батчи, пустые ленты, injection, tier-источники.
5. **Аналитика AI** — генерация, калибровка, спорные оценки.
6. **Диагностика системы** — ошибки AI, rescore, health.
7. **Модерация** — скрытие событий из ленты (reports — Phase E2).
8. **Экспорт** — CSV для разбора данных.

**Не цель v1:** полноценный CRM, multi-admin RBAC, отдельный React-фронт.

---

## 2. Архитектурные требования

| Требование | Решение |
|------------|---------|
| Backend | Встроить в существующий aiohttp-приложение (`app/main.py`) |
| Frontend | **Не** отдельный проект. HTML + **Jinja2** |
| Графики | **Chart.js** (CDN или static) |
| Шаблоны | Модули: `app/admin/routes/`, `app/admin/templates/` |
| Auth | Cookie-session, пароль из `ADMIN_PASSWORD` (ENV) |
| Хостинг | Railway, тот же сервис что webhook |
| Webhook | Админ-роуты **не должны** ломать `/webhook` и `/health` |

### 2.1 ENV

| Переменная | Обязательна | Описание |
|------------|-------------|----------|
| `ADMIN_PASSWORD` | Да (для доступа) | Пароль входа. Если пусто — `/admin/*` → **404** |
| `ADMIN_SESSION_TTL_HOURS` | Нет | Default: `24` |
| `ADMIN_ALLOWED_IPS` | Нет | Опционально, comma-separated (post-MVP) |

---

## 3. Авторизация

### Роуты

- `GET/POST /admin/login`
- `GET /admin/logout`
- Все `/admin/*` (кроме login) — только для авторизованной сессии

### Поведение

- Cookie-based session, **HttpOnly**, **Secure** в production (webhook mode).
- CSRF-токен на всех POST-формах.
- Пароль только в ENV, не в БД, не в логах.
- Неудачный login — generic error, без утечки «пароль неверный» vs «админка выключена».
- Session TTL по `ADMIN_SESSION_TTL_HOURS`.

---

## 4. Фундамент аналитики (обязательно до Dashboard и Funnels)

### 4.1 Таблица `admin_event_log`

Все ключевые действия пользователя и системы пишутся **синхронно** в сервисный слой (не только SQL-реконструкция).

```sql
admin_event_log (
  id uuid PK,
  user_id uuid NULL references users(id),
  event_name text NOT NULL,
  properties jsonb NOT NULL DEFAULT '{}',
  created_at timestamptz NOT NULL DEFAULT now()
)
-- index: (event_name, created_at), (user_id, created_at)
```

### 4.2 Каталог событий (v1)

| event_name | Когда | properties (пример) |
|------------|-------|------------------------|
| `user_registered` | Первое создание user | `telegram_id` |
| `user_seen` | Любое взаимодействие с ботом | — |
| `feed_started` | Создан или возобновлён батч | `batch_id`, `is_new_batch`, `batch_size` |
| `feed_empty` | Нет событий для ленты | — |
| `batch_created` | Новый `rating_batches` | `batch_id`, `requested_size`, `actual_size` |
| `batch_completed` | Батч завершён | `batch_id`, `actual_size` |
| `event_shown` | Impression created / shown | `event_id`, `batch_id`, `feed_tier` |
| `event_rated` | Оценка поставлена | `event_id`, `score`, `rating_scope` |
| `event_skipped` | Пропуск | `event_id`, `batch_id`, `feed_tier` |
| `event_created` | Автор создал событие | `event_id`, `event_type`, `source` |
| `event_deleted` | Автор удалил | `event_id` |
| `event_injected_into_batch` | Live injection | `event_id`, `viewer_user_id`, `batch_id`, `feed_tier` |
| `friend_invite_sent` | Share / invite flow | `friend_user_id` (optional) |
| `friendship_accepted` | Принята дружба | `friend_user_id` |
| `friendship_rejected` | Отклонён инвайт | `friend_user_id` (optional) |
| `notification_created` | Запись в notifications | `notification_type`, `event_id` |
| `notification_sent` | Успешная отправка | `notification_id` |
| `notification_failed` | Ошибка отправки | `notification_id`, `error` |
| `ai_generation_triggered` | Порог доступных < min | `available_count` |
| `ai_generation_completed` | Батч сгенерирован | `batch_id`, `count` |
| `ai_generation_failed` | Ошибка OpenAI | `error` |
| `settings_notifications_changed` | Toggle уведомлений | `enabled` |
| `settings_language_changed` | Смена языка контента | `language_code` |

Канонический список для UI и валидации: `app/analytics/event_catalog.py`.

**Инструментация:** все события из таблицы выше пишутся через `AnalyticsService.track()` из middleware/handlers/services. Друзья и AI — в `FriendshipService`, `AIGenerationService`; настройки — в `settings` handlers.

### 4.2.1 Шумные события

`user_seen` (каждое сообщение) и `event_shown` (каждый показ в батче) по умолчанию **скрыты** на странице Activity; включаются фильтром «показать шумные».

### 4.3 Миграция `event_impressions.feed_tier`

Для честной Feed Analytics добавить колонку:

```sql
alter table event_impressions
  add column if not exists feed_tier smallint;
-- 0=friend, 1=user, 2=seed, 3=ai — заполнять при show/inject
```

Без этого «показы по источникам» возможны только через тяжёлые join и будут неточны для friend-tier.

### 4.4 Daily aggregates (для Dashboard 90d / All)

Таблица `analytics_daily` (заполнять cron или при первом запросе дня):

- `date`, `new_users`, `active_users`, `events_created`, `ratings_count`, `ai_events_generated`, `feed_empty_count`, `batches_created`, `avg_batch_size`

Иначе Dashboard на длинных периодах перегрузит Supabase.

### 4.5 View `event_lifecycle_summary`

Агрегат **глобального** жизненного цикла события (не per-user). Источник: `events`, `event_impressions`, `ratings`. Отдельная таблица не обязательна — SQL view или materialized view.

```sql
-- Концептуально; точный SQL при реализации Phase C2
event_lifecycle_summary (
  event_id uuid PK,
  source event_source,
  event_type event_type,
  category text,
  created_at timestamptz,
  first_shown_at timestamptz,           -- min(event_impressions.shown_at)
  first_skipped_at timestamptz,         -- min(skipped_at) where status=skipped
  first_rated_at timestamptz,           -- min(ratings.created_at)
  first_community_rated_at timestamptz, -- min where rating_scope=community
  first_friend_rated_at timestamptz,    -- min where rating_scope=friend
  rated_at_5_total timestamptz,         -- время 5-й оценки (любой scope)
  rated_at_10_total timestamptz,
  rated_at_5_community timestamptz,     -- время 5-й community-оценки
  impressions_count int,
  skips_count int,
  ratings_total int,
  ratings_community int,
  ratings_friend int,
  skip_rate numeric,                    -- skips / impressions (where impressions > 0)
  hours_to_first_show numeric,          -- first_shown_at - created_at
  hours_to_first_rating numeric,
  pool_wait_hours numeric,              -- для ai_generated: first_shown - created
  is_deleted boolean,
  deleted_at timestamptz,
  is_feed_hidden boolean,
  hidden_at timestamptz,                -- post-migration, из admin_action_log или col
  ai_score numeric,
  community_user_score numeric,
  dispute_delta numeric                 -- abs(ai_score - community_user_score)
)
```

Обновление: on-read для MVP; materialized view + refresh cron — если список тормозит.

### 4.6 Таблица `admin_action_log`

Действия **администратора** (отдельно от user event log):

```sql
admin_action_log (
  id uuid PK,
  action text NOT NULL,        -- hide_event, unhide_event, dismiss_report, ...
  target_type text,            -- event, report, user
  target_id uuid,
  comment text,
  created_at timestamptz
)
```

---

## 5. Dashboard (`/admin`)

### 5.1 KPI-карточки

| Карточка | Источник |
|----------|----------|
| Users Total | `users` |
| New Users Today / 7d | `users.created_at` |
| Active Users Today / 7d | `user_seen` или `users.last_seen_at` |
| Events Total / Today | `events` |
| Ratings Total / Today | `ratings` |
| AI Events Total | `events.source = 'ai_generated'` |
| Avg Community Ratings per Event | `avg(community_ratings_count)` |
| Avg Batch Size | `avg(rating_batches.actual_size)` |
| Empty Feed Starts | `count(feed_empty)` из log |
| AI Generation Triggers (7d) | log |
| Pending AI Rescore | `events.scoring_calibration_version < current` |
| Events Without Impressions (24h+) | `event_lifecycle_summary`: created >24h ago, impressions_count=0 |
| Median Time to First Rating | `median(hours_to_first_rating)` за период |
| Median Skip Rate | `median(skip_rate)` по событиям с impressions ≥ 3 |

### 5.2 Графики (Chart.js)

Периоды: **7 / 30 / 90 / All**

- Новые пользователи / день
- Активные пользователи / день
- События / день
- Оценки / день
- AI generation / день
- Empty feed / день
- События: time-to-first-rating (median / день для cohort created)

### 5.3 Ops-блок (диагностика)

- Последние `ai_generation_failed` (5 шт.)
- Последние `notification_failed` (5 шт.)
- Счётчик событий на пересчёт калибровки
- Ссылка на `/health`

---

## 6. Пользователи

### 6.1 Список (`/admin/users`)

Таблица + пагинация. Фильтры:

- дата регистрации (from / to)
- `language_code`
- есть события (да/нет)
- есть оценки (да/нет)
- активность (last_seen за N дней)

Колонки: id, username, имя, язык, created_at, last_seen_at, events_count, ratings_count, friends_count.

### 6.2 Карточка (`/admin/users/{id}`)

- Профиль Telegram
- Друзья (список)
- События автора (ссылки)
- Статистика автора / оценщика (как в боте)
- **Timeline** — последние 100 записей из `admin_event_log`
- Активные / завершённые батчи

---

## 7. Воронки (`/admin/funnels`)

### 7.1 Определения шагов (канонические)

Воронка строится по **первому достижению** шага каждым пользователем (funnel по когорте регистрации — post-MVP).

| # | Шаг | Условие (первое вхождение) |
|---|-----|----------------------------|
| 1 | Registration | `user_registered` |
| 2 | First Feed | `feed_started` |
| 3 | First Event Viewed | `event_shown` |
| 4 | First Rating | `event_rated` |
| 5 | 5 Ratings | `count(event_rated) >= 5` |
| 6 | 10 Ratings | `count(event_rated) >= 10` |
| 7 | First Event Created | `event_created` |
| 8 | First Community Rating Received | на событии автора: первая `rating` с `scope=community` |
| 9 | Friend Invite Sent | `friend_invite_sent` |
| 10 | Friendship Accepted | `friendship_accepted` |
| 11 | First Friend Rating Received | на событии автора: первая `rating` с `scope=friend` |
| 12 | Returned Next Day | `user_seen` на day+1 после регистрации |
| 13 | Returned Within 7 Days | `user_seen` в днях 2–7 после регистрации |

UI: таблица — абсолютное число на шаге, % от Registration, % от предыдущего шага.

### 7.2 Post-MVP

- Когортная воронка (по неделе регистрации)
- Фильтр по языку

---

## 8. События

### 8.1 Список (`/admin/events`)

Фильтры:

- `source` (seed / user / ai_generated)
- `category`
- `original_language`
- `event_type` (real / hypothetical)
- диапазон `final_community_score`
- `is_deleted`
- `is_feed_hidden`
- только AI / только user

### 8.2 Карточка (`/admin/events/{id}`)

- original_text, normalized_text, action, context, category
- self_score, ai_score, community_user_score, final_community_score, friends_score
- **community_ai_weight**, **community_user_weight**, **scoring_calibration_version**
- все ratings (rater anonymized: user_id + scope + score + date)
- impressions (status, feed_tier, batch_id, timestamps)
- translations
- injection log (event_injected_into_batch)
- ссылка **«Lifecycle»** → строка в `/admin/events/lifecycle` + мини-timeline (те же milestones, compact)

**Карточка события** — сырые impressions/ratings и timeline.  
**Страница Lifecycle** — сравнимая таблица по всем событиям и сортировки «проблемных». Не дублировать полный UI дважды.

### 8.3 Event Lifecycle Analytics (`/admin/events/lifecycle`)

Отдельная страница: событие как **объект анализа** наравне с пользователем.

#### Назначение

Ответы на вопросы:

- какие события быстро набирают оценки;
- какие «умирают» без просмотров;
- какие часто пропускают;
- какие вызывают споры (в связке с AI Analytics).

#### Таблица (строка = событие)

Колонки (минимум):

| Колонка | Описание |
|---------|----------|
| Preview | усечённый `normalized_text` + ссылка на `/admin/events/{id}` |
| source / type | seed, user, ai_generated; real / hypothetical |
| created_at | создано |
| first_shown_at | первый показ **любому** пользователю |
| first_skipped_at | первый skip |
| first_rated_at | первая оценка (любой scope) |
| first_community_rated_at | первая `rating_scope=community` |
| first_friend_rated_at | первая `rating_scope=friend` |
| rated_at_5_total / _10_total | время достижения 5 и 10 оценок (всего) |
| rated_at_5_community | время 5 community-оценок |
| impressions / skips / ratings | счётчики |
| skip_rate | skips / impressions |
| hours_to_first_show / _rating | производные интервалы |
| deleted_at / hidden | конец жизни в ленте |
| dispute_delta | \|ai_score − community_user_score\| |

#### Milestones (канонические определения)

| Milestone | Условие |
|-----------|---------|
| Создано | `events.created_at` |
| Первое появление в ленте | `min(event_impressions.shown_at)` глобально |
| Первый skip | `min(skipped_at)` при `status=skipped` |
| Первая оценка | `min(ratings.created_at)` |
| Первая community-оценка | `min` при `rating_scope=community` |
| Первая friend-оценка | `min` при `rating_scope=friend` |
| 5 / 10 оценок | timestamp N-й записи в `ratings` (отдельно total и community) |
| Удалено | `events.deleted_at` (автор, soft delete) |
| Скрыто | `is_feed_hidden` или запись в `admin_action_log` |

`admin_event_log` для lifecycle **не обязателен в v1** — достаточно `event_impressions` + `ratings`.

#### Пресеты сортировки / фильтры

| Пресет | Условие |
|--------|---------|
| Без показов | `impressions_count=0` AND age > 24h |
| Высокий skip | `skip_rate >= 0.5` AND `impressions_count >= 3` |
| Быстрый набор | топ по возрастанию `hours_to_first_rating` |
| Медленный набор | `first_shown_at` not null, `ratings_total=0`, age > 48h |
| Спорные | `dispute_delta >= 3` AND `ratings_community >= 5` |
| AI в пуле | `source=ai_generated`, высокий `pool_wait_hours` |

Доп. фильтры: `source`, `category`, `event_type`, date range created, `is_deleted`, `is_feed_hidden`.

#### UI

- Таблица с пагинацией (50 строк).
- Клик по строке → `/admin/events/{id}` (детали + полный timeline).
- Опционально: sparkline «оценки по дням» post-MVP.

### 8.4 Действия модератора (Phase E)

| Действие | Поведение |
|----------|-----------|
| Hide from feed | `is_feed_hidden = true`, событие исключается из `_FEED_VISIBILITY_WHERE` |
| Unhide | обратно |
| — | Запись в `admin_action_log` + optional comment |

**Не путать** с `is_deleted` (удаление автором + обезличивание).

Действие `review event` **убрано из v1** — заменено статусами в `event_reports` (Phase E2).

---

## 9. Аналитика оценок (`/admin/ratings`)

- Распределение score −10…+10 (histogram)
- Средние: self / friends / community / AI
- Разбивка по `category`, `original_language`
- AI score distribution
- Сравнение self vs community (scatter или таблица отклонений)

---

## 10. Feed Analytics (`/admin/feed`)

| Метрика | Источник |
|---------|----------|
| Батчей создано / завершено | `rating_batches`, log |
| Средний / медианный `actual_size` | `rating_batches` |
| % батчей `< 30` | `actual_size < requested_size` |
| % батчей `< 10` | `actual_size < 10` |
| Empty feed starts | `feed_empty` log |
| Показы / оценки / skip по feed_tier | `event_impressions.feed_tier` |
| AI generation triggers / batches | log |
| **Injections** | `event_injected_into_batch` — count, по tier |
| События созданы, но 0 injections | cross: `event_created` без injection за N мин |

---

## 11. AI Analytics (`/admin/ai`)

### 11.1 Качество scoring

Таблица спорных событий:

- фильтр: `community_ratings_count >= 5` AND `abs(ai_score - community_user_score) >= 3`
- колонки: text, ai_score, community_user_score, final, weights, calibration_version, ratings_count

### 11.2 Генерация

- События `ai_generated` / день
- Успех vs `ai_generation_failed`
- Последние generation batches (`generation_batch_id`)

### 11.3 Rescore

- Сколько событий с устаревшей `scoring_calibration_version`
- Последний фоновый rescore (лог или метаданные в ENV/таблице)

---

## 12. Notifications (`/admin/notifications`)

| Метрика | Источник |
|---------|----------|
| created / sent / failed | log + `notifications` |
| failed | `notification_failed` OR (`is_sent=false` AND age > 1h) — до миграции `send_error` |
| users with notifications disabled | `users.notifications_enabled = false` |
| по типам | `new_ratings`, `first_friend_rating` |

**Миграция (Phase D):** `notifications.send_error text`, `failed_at timestamptz`.

`community_score_changed` — в боте не реализован; в админке показывать 0 до внедрения.

---

## 12.5 Activity Log (`/admin/activity`)

Журнал **всех действий пользователей** из `admin_event_log` — построчный просмотр с фильтрами (не агрегат как Funnels/Dashboard).

| Фильтр | Описание |
|--------|----------|
| Период | `date_from` … `date_to`, max **90 дней** (default 7) |
| User ID | UUID |
| Username / имя / telegram_id | поиск по `users` |
| Группа | user, events, feed, friends, notifications, ai, settings |
| Действие | конкретный `event_name` из §4.2 |
| Event ID | `properties->>'event_id'` |
| Шумные | по умолчанию скрыты `user_seen`, `event_shown` |

Таблица: время, действие (код + label), пользователь (ссылка на `/admin/users/{id}`), payload JSON, ссылка на event если есть.

С карточки пользователя — ссылка «Все действия пользователя» с предзаполненным `user_id`.

Export: тип `admin_event_log` на `/admin/export`.

**Backfill (migration `011_backfill_admin_event_log.sql`):** при первом деплое после Phase G восстанавливает прошлые действия из `users`, `events`, `ratings`, `event_impressions`, `friendships`, `rating_batches`, `notifications`. В payload: `"backfilled": true`. Live-track не дублируется.

---

## 13. Модерация и жалобы

### Phase E1 (admin-only)

- Hide / unhide event (см. §8.4)
- `admin_action_log`

### Phase E2 (reports)

Таблица `event_reports`:

```sql
event_reports (
  id uuid PK,
  event_id uuid references events(id),
  reporter_user_id uuid references users(id),
  reason text,
  status text check (status in ('open','reviewed','dismissed','action_taken')),
  admin_comment text,
  created_at timestamptz,
  resolved_at timestamptz
)
```

Экран `/admin/reports` — очередь open.

**Требует бота:** кнопка «Пожаловаться» на экране после оценки (отдельная задача в `03_DECISION_LOG`).

До Phase E2 reports-таблица не создаётся.

---

## 14. CSV Export (`/admin/export`)

Форматы: users, events, ratings, admin_event_log, ai_audit (спорные события), **event_lifecycle** (из view §4.5).

**Ограничения v1:**

- обязательный date range (max **90 дней**)
- лимит **50 000** строк; иначе сообщение «сузьте фильтр»
- POST + CSRF + confirm

Reports export — с Phase E2.

---

## 15. Навигация (sidebar)

```
Dashboard
Users
Activity         → /admin/activity
Funnels
Events
Event Lifecycle    → /admin/events/lifecycle
Ratings
Feed
AI
Notifications
Reports      ← скрыт до Phase E2
Export
System       ← версия, calibration_version, health, ENV flags (read-only)
```

Раздел **Settings** из исходного ТЗ **убран** — заменён на **System**.

---

## 16. Безопасность

- Все POST — CSRF.
- Cookie: HttpOnly, Secure (production), SameSite=Lax.
- Destructive actions — confirm dialog.
- Логи без паролей и session id.
- PII в CSV — только для внутреннего использования; не кэшировать export на диске сервера.
- `/admin` не индексируется (`robots` meta / `X-Robots-Tag: noindex`).

---

## 17. Roadmap реализации

### Phase A — Фундамент (блокирует всё остальное)

- [ ] Миграция `009_admin_analytics.sql`: `admin_event_log`, `admin_action_log`, `analytics_daily`, `event_impressions.feed_tier`, `events.is_feed_hidden`
- [ ] `AnalyticsService.track(...)` + вызовы из handlers/services
- [ ] Auth: login / logout / session middleware
- [ ] CSRF helper
- [ ] Базовый layout Jinja2 + sidebar

### Phase B — Dashboard + Funnels

- [ ] Dashboard KPI + графики (7/30/90)
- [ ] `analytics_daily` job
- [ ] Funnels page по каноническим определениям §7

### Phase C — Users + Events (read-only)

- [ ] Users list + detail + timeline
- [ ] Events list + detail

### Phase C2 — Event Lifecycle

- [ ] SQL view `event_lifecycle_summary` (§4.5)
- [ ] `/admin/events/lifecycle` — таблица, пресеты, фильтры (§8.3)
- [ ] KPI lifecycle на Dashboard (§5.1)
- [ ] Ссылка Lifecycle на карточке события (§8.2)
- [ ] CSV export `event_lifecycle`

### Phase D — Ratings + Feed + AI + Notifications

- [ ] Ratings analytics
- [ ] Feed analytics (включая injection)
- [ ] AI analytics + disputed scores
- [ ] Notifications stats
- [ ] Миграция `notifications.send_error` (если нужно)

### Phase E1 — Moderation

- [ ] Hide / unhide event
- [ ] `admin_action_log` UI

### Phase E2 — Reports (после UX в боте)

- [ ] `event_reports` + `/admin/reports`
- [ ] Кнопка «Пожаловаться» в боте

### Phase F — Export + polish

- [ ] CSV export с лимитами
- [ ] System page
- [ ] Тесты admin routes (auth, CSRF)

---

## 18. Критерии приёмки

1. Админка доступна в production при заданном `ADMIN_PASSWORD`.
2. Webhook и `/health` работают без регрессий.
3. Воронка считается по `admin_event_log`, не по хрупким join.
4. Feed analytics показывает tier-разбивку и injections.
5. Карточка события показывает scoring weights и calibration version.
6. Hide event исключает событие из ленты, не удаляет его.
7. Все страницы за auth; без пароля — 404.
8. CSV export с date range и лимитом.
9. Admin actions пишутся в `admin_action_log`.
10. Event Lifecycle: view, страница `/admin/events/lifecycle`, пресеты без показов / skip / спорные.
11. Документ `04_ADMIN_DASHBOARD_SPEC.md` обновлён в changelog при изменениях.

---

## 19. Зависимости от текущего кода

| Что есть | Что нужно добавить |
|----------|-------------------|
| `users.last_seen_at` | + `user_seen` в log на каждое действие |
| `rating_batches.actual_size` | + log `batch_created` / `batch_completed` |
| `event_impressions` | + `feed_tier`; lifecycle: `shown_at`, `skipped_at`, `status` |
| `ratings.created_at`, `rating_scope` | lifecycle milestones |
| `events.source`, scoring audit cols | использовать в UI + lifecycle |
| `notifications.is_sent` | + `notification_failed` event / cols |
| Нет hide | + `is_feed_hidden` |
| Нет admin | весь модуль `app/admin/` |

---

## 20. Вне scope v1

- Multi-admin, роли
- Ban user (можно добавить в v1.2 по запросу)
- Отдельный React frontend
- FastAPI
- Real-time WebSocket dashboard
- Публичная аналитика

---

## Changelog

| Версия | Дата | Изменения |
|--------|------|-----------|
| 1.0 | — | Исходный docx (ChatGPT): полный scope, event log в Phase E |
| 1.1 | 2026-06-10 | Переписано после ревью: event log в Phase A; каноническая воронка; `feed_tier`; `is_feed_hidden`; `admin_action_log`; injection metrics; ops block; daily aggregates; reports отложены (E2); убран `review event`; Settings → System; лимиты CSV |
| 1.2 | 2026-06-11 | Event Lifecycle Analytics: view `event_lifecycle_summary`, `/admin/events/lifecycle`, Phase C2, Dashboard KPI, export, связь с карточкой события |

### Шаблон для следующих правок

```
| 1.x | YYYY-MM-DD | Кратко: что уточнили и какой раздел затронут |
```
