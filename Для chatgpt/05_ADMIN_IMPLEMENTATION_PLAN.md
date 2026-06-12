# План работ: Web Admin Dashboard

**Версия:** 1.0  
**Дата:** 2026-06-11  
**ТЗ:** `04_ADMIN_DASHBOARD_SPEC.md` v1.2  
**Статус кода:** админка **не начата** (`app/admin/` отсутствует)

> Живой документ: отмечайте `[x]` по мере выполнения. При изменении scope — правьте здесь и Changelog в `04_…`.

---

## 0. Принципы

1. **Сначала данные, потом UI** — Phase A (миграция + instrumentation) блокирует воронки и Dashboard.
2. **Read-only раньше write** — модерация (hide) только после просмотра Events.
3. **Не ломать webhook** — admin routes регистрировать в том же `aiohttp` app, smoke-test `/health` и `/webhook` после каждой фазы.
4. **Деплой по фазам** — после A+B уже полезно в проде (login + dashboard + funnels).
5. **Один PR ≈ одна фаза** (или подфаза) — проще откатить.

---

## 1. Целевая структура кода

```
app/
  admin/
    __init__.py
    app.py                    # setup_admin_routes(app, pool)
    auth.py                   # session, login, middleware
    csrf.py
    templates/
      base.html
      login.html
      dashboard.html
      ...
    static/                   # optional: admin.css
    routes/
      dashboard.py
      users.py
      funnels.py
      events.py
      lifecycle.py
      ratings.py
      feed.py
      ai.py
      notifications.py
      moderation.py
      export.py
      system.py
    services/
      analytics_service.py    # track() → admin_event_log
      admin_queries.py        # SQL для страниц
      funnel_service.py
      lifecycle_service.py
      export_service.py
      daily_aggregates.py
  db/
    migrations/
      009_admin_analytics.sql
      010_notifications_send_error.sql   # Phase D, опционально
    repositories/
      admin_event_log.py
      admin_action_log.py
```

**Точки интеграции в существующий код:**

| Место | Что добавить |
|-------|----------------|
| `app/main.py` | `setup_admin_routes(app, pool)` после webhook |
| `app/config.py` | `admin_password`, `admin_session_ttl_hours` |
| `app/bot/middlewares.py` | `analytics.track("user_seen")` |
| `app/bot/handlers/start.py` | `user_registered` |
| `app/services/feed_service.py` | feed_started, feed_empty, batch_*, injection |
| `app/services/rating_service.py` | event_rated, event_skipped |
| `app/services/event_service.py` | event_created, event_deleted |
| `app/services/notification_service.py` | notification_* |
| `app/services/ai_generation_service.py` | ai_generation_* |
| `app/bot/handlers/friends.py` | invite, friendship_accepted |
| `app/db/repositories/impressions.py` | писать `feed_tier` при show/inject |
| `app/db/repositories/events.py` | `_FEED_VISIBILITY_WHERE` + `is_feed_hidden` |

---

## 2. Оценка сроков (один разработчик + Cursor)

| Фаза | Содержание | Оценка |
|------|------------|--------|
| **A** | Фундамент | 3–5 дней |
| **B** | Dashboard + Funnels | 3–4 дня |
| **C** | Users + Events | 2–3 дня |
| **C2** | Event Lifecycle | 2–3 дня |
| **D** | Ratings, Feed, AI, Notifications | 4–5 дней |
| **E1** | Moderation hide | 1–2 дня |
| **F** | Export + System + тесты | 2–3 дня |
| **E2** | Reports + бот | отдельно, 3+ дня |

**До полезной админки в проде (A+B):** ~1–1.5 недели.  
**До полного v1 без E2:** ~3–4 недели.

---

## 3. Phase A — Фундамент

**Цель:** миграция, трекинг, auth, пустой layout. Без этого остальное — на неточных SQL.

### A.1 Миграция `009_admin_analytics.sql`

- [x] `admin_event_log` + индексы
- [x] `admin_action_log`
- [x] `analytics_daily`
- [x] `event_impressions.feed_tier smallint`
- [x] `events.is_feed_hidden boolean default false`
- [ ] SQL view-заглушки не нужны — только таблицы

**Проверка:** `run_migrations` на локальной БД без ошибок.

### A.2 AnalyticsService

- [x] `AnalyticsService.track(user_id, event_name, **properties)` — не роняет бота
- [x] `AdminEventLogRepository`
- [x] Unit-test: track пишет строку

### A.3 Instrumentation (по каталогу §4.2 ТЗ)

Приоритет **P0** (для воронки и dashboard):

- [x] `user_registered` — middleware при `is_new`
- [x] `user_seen` — middleware
- [x] `feed_started`, `feed_empty`
- [x] `batch_created`, `batch_completed`
- [x] `event_shown`, `event_rated`, `event_skipped`
- [x] `event_created`, `event_deleted`

Приоритет **P1** (для Feed / AI страниц):

- [x] `event_injected_into_batch`
- [ ] `ai_generation_triggered`, `_completed`, `_failed`
- [x] `notification_created`, `_sent`, `_failed`
- [ ] `friend_invite_sent`, `friendship_accepted`

### A.4 feed_tier в impressions

- [x] При `create_batch_impressions` / `inject_into_batch` — передавать tier
- [ ] Backfill не обязателен (старые impressions без tier — null в аналитике)

### A.5 Admin auth

- [x] `ADMIN_PASSWORD` в `config.py` + `.env.example`
- [x] Session middleware (signed cookie)
- [x] `GET/POST /admin/login`, `GET /admin/logout`
- [x] Если пароль пуст → все `/admin/*` → **404**
- [x] `HttpOnly`, `Secure` при webhook mode

### A.6 Каркас UI

- [x] Jinja2 env в `app/admin/templates.py`
- [x] `base.html` — sidebar (пункты disabled до фазы)
- [x] `login.html`, `home.html`
- [x] CSRF: модуль `csrf.py` (формы POST — Phase E/F)
- [x] `setup_admin_routes(app, pool)` в `main.py` (polling + webhook)

### A.7 Тесты Phase A

- [x] `/admin` без auth → redirect login
- [x] login успешный → cookie
- [x] admin disabled → 404
- [ ] `/webhook` и `/health` без регрессий (smoke на деплое)

**Definition of Done A:** логин работает локально; события пишутся в `admin_event_log` при типичном сценарии (/start → rate → add).

---

## 4. Phase B — Dashboard + Funnels

**Цель:** ответ на «где отваливаются» без ручного SQL.

### B.1 Daily aggregates

- [x] `DailyAggregatesService.refresh(date)` — upsert в `analytics_daily`
- [x] Вызов при открытии Dashboard (backfill за выбранный период)
- [ ] Backfill script / management command за последние 90 дней (одноразово)

### B.2 Dashboard `/admin`

- [x] KPI-карточки §5.1 (SQL в `admin_queries.py`)
- [x] Chart.js: 7/30/90/all — users, events, ratings, AI gen, empty feed
- [x] Ops-блок: последние AI/notification failures из log
- [x] Таблица event_name (7d) + последние записи лога (расшифровка для пользователя)

### B.3 Funnels `/admin/funnels`

- [x] `FunnelService` — 13 шагов по §7.1
- [x] Таблица: count, % от registration, % от prev step
- [x] Шаги 8, 11 — join `ratings` на события автора

### B.4 Тесты Phase B

- [ ] Funnel на фикстурах с БД
- [x] Dashboard рендерится без 500

**DoD B:** Roman может открыть Dashboard и Funnels в проде и увидеть реальные цифры.

**Деплой B** — первый **полезный** релиз админки.

---

## 5. Phase C — Users + Events

### C.1 Users `/admin/users`

- [x] Список + пагинация + фильтры §6.1
- [x] Detail `/admin/users/{id}` — профиль, друзья, события, stats summary
- [x] Timeline — последние 100 из `admin_event_log`

### C.2 Events `/admin/events`

- [x] Список + фильтры §8.1
- [x] Detail `/admin/events/{id}` — полная карточка §8.2 (weights, ratings, impressions, translations)

**DoD C:** можно разобрать инцидент «событие Elena не попало к Roman» по user + event cards.

---

## 6. Phase C2 — Event Lifecycle

**Цель:** событие как объект аналитики.

### C2.1 SQL

- [x] View `event_lifecycle_summary` §4.5
- [x] Индексы на `event_impressions(event_id)`, `ratings(event_id)` — уже есть; при медленности — mat. view

### C2.2 UI `/admin/events/lifecycle`

- [x] Таблица + пагинация 50
- [x] Пресеты §8.3 (без показов, high skip, быстрый/медленный, спорные, AI pool)
- [x] Ссылка с event detail → lifecycle row

### C2.3 Dashboard KPI

- [x] Events without impressions 24h+ (было в Phase B)
- [x] Median time to first rating, median skip rate

**DoD C2:** пресет «без показов» показывает застрявшие AI/seed события.

---

## 7. Phase D — Ratings, Feed, AI, Notifications

Параллелить можно после C; страницы независимы.

### D.1 `/admin/ratings` §9

- [x] Histogram −10…+10
- [x] Breakdown by category, language

### D.2 `/admin/feed` §10

- [x] Batch stats, tier breakdown (требует `feed_tier`)
- [x] Injection counts из log

### D.3 `/admin/ai` §11

- [x] Disputed events table
- [x] Generation stats, rescore counter

### D.4 `/admin/notifications` §12

- [x] created/sent/failed
- [ ] Опционально миграция `010` — `send_error`, `failed_at` (отложено)

**DoD D:** Feed tier chart не пустой на проде после недели трафика.

---

## 8. Phase E1 — Moderation

### E1.1 Hide event

- [x] POST hide/unhide + CSRF + confirm
- [x] Update `events.is_feed_hidden`
- [x] Patch `_FEED_VISIBILITY_WHERE` в `events.py`
- [x] `admin_action_log` запись

### E1.2 UI

- [x] Кнопки на event detail
- [x] Фильтр `is_feed_hidden` в events list

**DoD E1:** скрытое событие не появляется в новых батчах.

---

## 9. Phase F — Export, System, polish

### F.1 `/admin/export`

- [x] Форма: тип, date range, POST + CSRF
- [x] Streaming CSV, лимит 50k
- [x] Типы: users, events, ratings, admin_event_log, ai_audit, event_lifecycle

### F.2 `/admin/system`

- [x] Версия/commit (ENV или файл)
- [x] `SCORING_CALIBRATION_VERSION`
- [x] Health link, флаги ENV (без секретов)

### F.3 Тесты и hardening

- [x] CSRF на всех POST
- [x] `X-Robots-Tag: noindex` на admin layout
- [ ] README / DEPLOY: `ADMIN_PASSWORD` для Railway

**DoD F:** критерии приёмки §18 ТЗ (все 11 пунктов).

---

## 9.1 Phase G — Activity Log + полный track

### G.1 Инструментация

- [x] Каталог событий `app/analytics/event_catalog.py`
- [x] Друзья: `friend_invite_sent`, `friendship_accepted`, `friendship_rejected`
- [x] AI: `ai_generation_triggered/completed/failed`
- [x] Настройки: `settings_notifications_changed`, `settings_language_changed`

### G.2 `/admin/activity`

- [x] Фильтры: период, user, username, группа, event_name, event_id
- [x] Пагинация, ссылки user/event
- [x] Ссылка с user detail
- [x] Nav + тесты

**DoD G:** любое типичное действие в боте видно в Activity за выбранный период.

---

## 10. Phase E2 — Reports (отдельный релиз)

Не блокирует v1 админки.

- [ ] Миграция `event_reports`
- [ ] `/admin/reports`
- [ ] Кнопка «Пожаловаться» в боте (`rate.py` после оценки)
- [ ] Export reports

---

## 11. Порядок работ (рекомендуемый backlog)

```
Спринт 1:  A.1 → A.7          (миграция, track P0, auth, layout)
Спринт 2:  A.3 P1, B.1 → B.4  (track остальное, dashboard, funnels) → DEPLOY
Спринт 3:  C.1 → C.2          (users, events) → DEPLOY
Спринт 4:  C2.1 → C2.3        (lifecycle) → DEPLOY
Спринт 5:  D.1 → D.4          (analytics pages)
Спринт 6:  E1 + F             (moderation, export, system, tests) → DEPLOY v1
Спринт 7:  G                  (activity log, полный track) → DEPLOY
Позже:     E2                 (reports + бот)
```

---

## 12. Чеклист деплоя (каждая фаза)

1. [ ] `ADMIN_PASSWORD` в Railway Variables
2. [ ] Миграции применились (лог startup)
3. [ ] `GET /health` → ok
4. [ ] Webhook: бот отвечает в Telegram
5. [ ] `GET /admin` → login (не 500)
6. [ ] Smoke: один сценарий бота → строка в `admin_event_log`

---

## 13. Риски и митигация

| Риск | Митигация |
|------|-----------|
| Тяжёлые запросы Dashboard на All | `analytics_daily`, лимит периода |
| `track()` замедляет бота | async insert, try/except, не await в критическом path или отдельная очередь |
| Session без HTTPS локально | `Secure` только при `is_webhook` |
| Старые данные без log | Funnel только с даты включения A; lifecycle из impressions/ratings — ретроактивно |
| feed_tier null на старых impressions | Показывать «unknown tier» в Feed analytics |

---

## 14. Зависимости (pip)

Вероятно понадобится:

- `aiohttp-jinja2` или встроенный Jinja2 setup
- `itsdangerous` — подпись session cookie (если не своя реализация)

Проверить `requirements.txt` перед Phase A.

---

## 15. Связь с пакетом ChatGPT

| Документ | Роль |
|----------|------|
| `04_ADMIN_DASHBOARD_SPEC.md` | Что строим (scope) |
| `05_ADMIN_IMPLEMENTATION_PLAN.md` | Как и в каком порядке строим |
| `01_PROJECT_CONTEXT.md` | Контекст бота для instrumentation |
| `03_DECISION_LOG.md` | Не предлагать отклонённое (shuffle, AI до 30, …) |

После завершения фазы — обновить чеклисты здесь и Changelog в `04_…`.

---

## Changelog

| Версия | Дата | Изменения |
|--------|------|-----------|
| 1.0 | 2026-06-11 | Первый план: фазы A–F, структура кода, спринты, DoD, деплой |
