# LifeLedger MVP v1.0 — Architecture

Файл: `architecture.md`  
Назначение: техническая архитектура MVP Telegram-бота LifeLedger для реализации в Cursor.  
Связанные документы:

- `PRD.md`
- `database_schema.md`
- `telegram_ux.md`

---

# 1. Цель архитектуры

Архитектура MVP должна позволить быстро собрать рабочий Telegram-бот без избыточной сложности, но с учетом будущего развития продукта.

MVP должен поддерживать:

1. Регистрацию пользователей Telegram.
2. Ленту событий для оценки как главный экран.
3. Добавление реальных и гипотетических событий.
4. AI-обработку события:
   - определение языка;
   - выделение Event Time;
   - выделение Action;
   - выделение Context;
   - определение Category;
   - нормализация текста;
   - AI Score.
5. Перевод событий на язык оценщика.
6. Оценку событий пользователями.
7. Три вида оценок события:
   - самооценка;
   - оценка друзей;
   - оценка сообщества.
8. Подборки до 30 событий.
9. Исключение повторного показа событий.
10. Друзей с подтверждением.
11. Рейтинги и средние оценки.
12. Статистику автора и оценщика.
13. Удаление событий с обезличиванием.
14. Уведомления.

---

# 2. Рекомендуемый стек

## 2.1. Backend

Python 3.11+

## 2.2. Telegram Bot

aiogram 3.x

## 2.3. API

FastAPI

На первом этапе FastAPI может использоваться для:

- health-check;
- webhooks Telegram;
- внутренних административных endpoint-ов;
- будущей интеграции с мобильным приложением или web-интерфейсом.

## 2.4. Database

Supabase PostgreSQL

## 2.5. AI Provider

OpenAI API или Claude API.

В коде желательно сделать абстрактный слой `AIProvider`, чтобы можно было заменить поставщика без переписывания бизнес-логики.

## 2.6. Hosting

Подходит:

- Render;
- Railway;
- Fly.io;
- VPS;
- Supabase Edge Functions не обязательны.

## 2.7. Background Jobs

Для MVP можно начать без отдельной очереди.

Варианты:

### Простая версия MVP

- async tasks внутри приложения;
- периодические cron-задачи;
- Supabase Scheduled Functions;
- APScheduler.

### Более зрелая версия

- Celery + Redis;
- RQ + Redis;
- Dramatiq.

Для MVP рекомендуется начать с простой версии.

---

# 3. Высокоуровневая схема

```text
Telegram User
     ↓
Telegram Bot API
     ↓
aiogram handlers
     ↓
Application Services
     ↓
PostgreSQL / Supabase
     ↓
AI Provider
```

Основные сервисы приложения:

```text
UserService
EventService
AIService
TranslationService
RatingService
FeedService
FriendshipService
StatsService
NotificationService
```

---

# 4. Модульная структура проекта

Рекомендуемая структура:

```text
lifeledger-bot/
│
├── app/
│   ├── main.py
│   ├── config.py
│   ├── logging_config.py
│   │
│   ├── bot/
│   │   ├── dispatcher.py
│   │   ├── keyboards.py
│   │   ├── middlewares.py
│   │   └── handlers/
│   │       ├── start.py
│   │       ├── rate.py
│   │       ├── add_event.py
│   │       ├── events.py
│   │       ├── stats.py
│   │       ├── friends.py
│   │       ├── settings.py
│   │       └── help.py
│   │
│   ├── db/
│   │   ├── connection.py
│   │   ├── repositories/
│   │   │   ├── users.py
│   │   │   ├── events.py
│   │   │   ├── ratings.py
│   │   │   ├── friendships.py
│   │   │   ├── impressions.py
│   │   │   ├── translations.py
│   │   │   ├── stats.py
│   │   │   └── notifications.py
│   │   └── migrations/
│   │
│   ├── services/
│   │   ├── user_service.py
│   │   ├── event_service.py
│   │   ├── ai_service.py
│   │   ├── translation_service.py
│   │   ├── rating_service.py
│   │   ├── feed_service.py
│   │   ├── friendship_service.py
│   │   ├── stats_service.py
│   │   └── notification_service.py
│   │
│   ├── schemas/
│   │   ├── ai.py
│   │   ├── events.py
│   │   ├── ratings.py
│   │   ├── stats.py
│   │   └── users.py
│   │
│   └── utils/
│       ├── time.py
│       ├── scoring.py
│       ├── language.py
│       └── text.py
│
├── docs/
│   ├── PRD.md
│   ├── database_schema.md
│   ├── telegram_ux.md
│   └── architecture.md
│
├── tests/
│
├── .env.example
├── requirements.txt
└── README.md
```

---

# 5. Основные сервисы

## 5.1. UserService

Ответственность:

- создать пользователя при `/start`;
- обновить Telegram username, language_code, last_seen_at;
- получить пользователя по Telegram ID;
- обработать настройки уведомлений.

Ключевые методы:

```python
get_or_create_user(telegram_user) -> User
update_last_seen(user_id) -> None
set_notifications_enabled(user_id, enabled: bool) -> None
```

---

## 5.2. EventService

Ответственность:

- создать событие;
- сохранить исходный текст;
- вызвать AIService;
- сохранить Action / Context / Category / Normalized Text;
- сохранить self_score;
- сохранить AI Score;
- удалить событие с обезличиванием;
- получить события пользователя.

Ключевые методы:

```python
create_event(author_id, event_type, original_text, self_score) -> Event
delete_event(event_id, author_id) -> None
get_user_events(user_id) -> list[Event]
get_event_details(event_id, user_id) -> Event
```

---

## 5.3. AIService

Ответственность:

- определить язык;
- выделить event_time;
- выделить action;
- выделить context;
- определить category;
- сформировать normalized_text;
- сформировать ai_score;
- переводить текст.

Ключевые методы:

```python
analyze_event(original_text: str, user_language: str) -> EventAnalysis
translate_event(normalized_text: str, target_language: str) -> str
score_event(normalized_text: str, action: str, context: str) -> float
```

Для MVP можно объединить анализ и оценку в один AI-запрос.

---

## 5.4. TranslationService

Ответственность:

- проверить наличие перевода;
- создать перевод при необходимости;
- вернуть текст события на языке оценщика.

Ключевой метод:

```python
get_or_create_translation(event_id, target_language) -> str
```

---

## 5.5. RatingService

Ответственность:

- принять оценку пользователя;
- определить rating_scope: friend/community;
- запретить оценку собственного события;
- запретить повторную оценку;
- создать запись ratings;
- обновить event_impression;
- пересчитать оценки события;
- инициировать пересчет статистики.

Ключевые методы:

```python
rate_event(event_id, rater_id, score) -> RatingResult
skip_event(event_id, user_id) -> None
recalculate_event_scores(event_id) -> None
```

---

## 5.6. FeedService

Ответственность:

- сформировать подборку до 30 событий;
- учитывать приоритеты:
  1. события друзей;
  2. новые события;
  3. события с недостаточным количеством оценок;
- исключать уже просмотренные события;
- исключать события самого пользователя;
- перемешивать результат;
- создавать rating_batch;
- создавать event_impressions.

Ключевые методы:

```python
get_or_create_current_batch(user_id) -> RatingBatch
create_new_batch(user_id, size=30) -> RatingBatch
get_next_event(user_id) -> EventForRating | None
```

---

## 5.7. FriendshipService

Ответственность:

- создать приглашение;
- обработать вход по invite link;
- создать pending friendship;
- подтвердить дружбу;
- отклонить дружбу;
- получить список друзей.

Ключевые методы:

```python
create_invite_link(user_id) -> str
handle_invite(inviter_id, invitee_id) -> Friendship
accept_friendship(friendship_id, user_id) -> None
get_friends(user_id) -> list[User]
are_friends(user_a, user_b) -> bool
```

---

## 5.8. StatsService

Ответственность:

- считать рейтинги автора;
- считать средние оценки автора;
- считать динамику за 7/30/90 дней;
- считать статистику оценщика:
  - оценено событий;
  - вы оценивали;
  - оценивало сообщество;
  - отклонение.

Ключевые методы:

```python
calculate_author_stats(user_id) -> AuthorStats
calculate_evaluator_stats(user_id) -> EvaluatorStats
create_user_rating_snapshot(user_id, period_start, period_end) -> None
```

---

## 5.9. NotificationService

Ответственность:

- создавать уведомления;
- отправлять уведомления, если они включены;
- не спамить пользователя;
- группировать события при необходимости.

Ключевые методы:

```python
notify_new_ratings(event_id) -> None
notify_first_friend_rating(event_id) -> None
notify_community_score_changed(event_id, old_score, new_score) -> None
```

---

# 6. AI Pipeline

## 6.1. Вход

Пользовательский текст:

```text
В прошлую субботу я кинул камнем в собаку, которая рычала и угрожала напасть на моего ребенка.
```

## 6.2. AI должен вернуть JSON

Пример:

```json
{
  "original_language": "ru",
  "event_time_text": "в прошлую субботу",
  "event_time_iso": null,
  "action": "Кинул камнем в собаку",
  "context": "Собака рычала и угрожала напасть на ребенка",
  "category": "животные/дети",
  "normalized_text": "Родитель кинул камнем в собаку, которая рычала и казалась угрозой для ребенка.",
  "ai_score": 2,
  "score_explanation": "Действие может быть оправдано защитой ребенка, но связано с причинением вреда животному."
}
```

## 6.3. Требования к AI JSON

AI должен возвращать валидный JSON.

Поля:

```text
original_language
event_time_text
event_time_iso
action
context
category
normalized_text
ai_score
score_explanation
```

`score_explanation` можно сохранять, но в MVP не показывать пользователю.

## 6.4. AI Score

Диапазон:

```text
-10 .. +10
```

Можно хранить как numeric.

Для интерфейса можно округлять до целого или одного знака.

## 6.5. Принцип нормализации

AI не должен удалять контекст, который влияет на оценку.

Плохая нормализация:

```text
Человек кинул камнем в собаку.
```

Хорошая нормализация:

```text
Родитель кинул камнем в собаку, которая рычала и казалась угрозой для ребенка.
```

---

# 7. Translation Pipeline

## 7.1. Когда нужен перевод

Когда язык оценщика отличается от языка normalized_text.

## 7.2. Алгоритм

```text
get_event_for_user(event_id, user_language)
↓
check event_translations(event_id, user_language)
↓
if exists: return translated_text
↓
else: AI translate normalized_text
↓
save translation
↓
return translated_text
```

## 7.3. Требования к переводу

Перевод должен быть смысловым, а не дословным.

Нельзя искажать:

- действие;
- контекст;
- степень угрозы;
- последствия;
- моральный смысл.

---

# 8. Community Scoring Engine

## 8.1. Данные

Для каждого события:

```text
ai_score
community_user_score
final_community_score
community_ratings_count
```

## 8.2. Формула

```text
final_community_score =
ai_score * ai_weight +
community_user_score * user_weight
```

```text
ai_weight + user_weight = 1
```

## 8.3. Весовая функция MVP

Рекомендуемая таблица:

```text
0 оценок:    AI 100%, Users 0%
10 оценок:   AI 90%,  Users 10%
50 оценок:   AI 80%,  Users 20%
100 оценок:  AI 50%,  Users 50%
500 оценок:  AI 20%,  Users 80%
1000 оценок: AI 0%,   Users 100%
```

Для промежуточных значений можно использовать ближайший нижний порог или линейную интерполяцию.

Для MVP проще использовать ближайший нижний порог.

## 8.4. Если community_user_score отсутствует

Если пользовательских оценок нет:

```text
final_community_score = ai_score
```

---

# 9. Friends Scoring Engine

## 9.1. Friends Score

```text
friends_score = average(score)
where rating_scope = 'friend'
```

## 9.2. Если оценок друзей нет

Показывать:

```text
Друзья: —
```

Не показывать:

```text
Друзья: 0
```

## 9.3. Рейтинг друзей

Считать только по событиям, у которых есть friends_score.

Не ждать, пока все события пользователя получат оценки друзей.

---

# 10. Feed Engine

## 10.1. Размер подборки

```text
batch_size = 30
```

Это не дневной лимит.

Пользователь может запросить следующую подборку.

## 10.2. Исключения

Не включать:

- удаленные события;
- события самого пользователя;
- события, которые пользователь уже видел;
- события, которые пользователь оценил;
- события, которые пользователь пропустил.

## 10.3. Приоритеты

### Priority 1: Friends events

События авторов, которые являются accepted friends.

### Priority 2: New community events

Новые события сообщества.

### Priority 3: Under-rated events

События с малым количеством оценок.

## 10.4. Перемешивание

После отбора события перемешиваются.

Пользователь не видит источник.

## 10.5. Создание impressions

При формировании подборки для каждого события создать `event_impressions` со статусом `shown`.

---

# 11. Rating Flow

## 11.1. Оценка события

```text
User presses score button
↓
validate event is available
↓
validate user is not author
↓
validate user did not rate event before
↓
determine rating_scope
↓
create rating
↓
update impression = rated
↓
recalculate event scores
↓
recalculate stats
↓
show own score and community score
```

## 11.2. Пропуск события

```text
User presses skip
↓
update impression = skipped
↓
show next event
```

---

# 12. Statistics Engine

## 12.1. Author Stats

### Rating totals

```text
self_rating_total = sum(self_score)

friends_rating_total = sum(friends_score where friends_score is not null)

community_rating_total = sum(final_community_score)
```

### Average scores

```text
self_average_score = avg(self_score)

friends_average_score = avg(friends_score where friends_score is not null)

community_average_score = avg(final_community_score)
```

## 12.2. Periods

Поддержать:

```text
all_time
7_days
30_days
90_days
```

Для периода использовать:

```text
event_time if exists else created_at
```

## 12.3. Evaluator Stats

По событиям, которые пользователь оценил:

```text
rated_events_count = count(ratings)

user_average_given_score = avg(ratings.score)

community_average_for_same_events = avg(events.final_community_score)

deviation =
user_average_given_score -
community_average_for_same_events
```

---

# 13. Delete / Anonymization Flow

## 13.1. Пользователь удаляет событие

```text
User confirms delete
↓
set is_deleted = true
↓
set deleted_at = now()
↓
set author_user_id = null
↓
set anonymized_after_delete = true
↓
remove from future feed
↓
exclude from author ratings
```

## 13.2. Что можно оставить

Обезличенно можно оставить:

- normalized_text;
- action;
- context;
- category;
- ratings;
- aggregate scores.

## 13.3. Что нельзя оставить привязанным к пользователю

- author_user_id;
- связь с Telegram ID;
- связь с профилем пользователя.

---

# 14. Notification Architecture

## 14.1. Не спамить

Не отправлять уведомление на каждую отдельную оценку.

## 14.2. Триггеры

- появились новые оценки;
- появилась первая оценка друзей;
- существенно изменилась оценка сообщества.

## 14.3. Настройка

Пользователь может отключить уведомления.

---

# 15. Error Handling

## 15.1. AI failed

Если AI-анализ не сработал:

- сохранить original_text;
- normalized_text = original_text;
- category = null;
- ai_score = 0 или повторить позже.

Рекомендуется: повторить позже, но не блокировать пользователя.

## 15.2. Translation failed

Если перевод не сработал:

- показать normalized_text на исходном языке;
- можно добавить короткую пометку "перевод временно недоступен".

## 15.3. DB error

Показать пользователю:

```text
Произошла ошибка. Попробуйте еще раз.
```

Логировать ошибку.

---

# 16. Configuration

`.env` должен включать:

```text
TELEGRAM_BOT_TOKEN=
DATABASE_URL=
SUPABASE_URL=
SUPABASE_SERVICE_ROLE_KEY=
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
AI_PROVIDER=openai
DEFAULT_LANGUAGE=en
BATCH_SIZE=30
```

---

# 17. Logging

Логировать:

- регистрацию пользователя;
- создание события;
- AI-анализ;
- ошибки AI;
- создание перевода;
- оценку события;
- пропуск события;
- создание подборки;
- удаление события;
- отправку уведомлений.

Не логировать чувствительный текст событий в production-логах без необходимости.

---

# 18. Security / Privacy

## 18.1. Не раскрывать автора

Ни в одном пользовательском интерфейсе оценщик не видит автора события.

## 18.2. Не раскрывать источник события

Не показывать, что событие от друга.

## 18.3. Не показывать алгоритм

Не показывать:

- AI Score;
- веса;
- количество голосов.

## 18.4. Удаление

Удаление должно убирать связь события с пользователем.

---

# 19. Minimal MVP Implementation Order

## Phase 1: Core Bot

1. /start
2. user registration
3. main rate screen
4. static test events

## Phase 2: Events

1. /add
2. create event
3. self_score
4. list my events

## Phase 3: Ratings

1. feed batches
2. impressions
3. rate event
4. skip event
5. recalculate scores

## Phase 4: AI

1. event analysis
2. normalized text
3. AI Score
4. translation

## Phase 5: Friends

1. invite link
2. pending friendship
3. accept friendship
4. friend scoring

## Phase 6: Stats

1. author stats
2. evaluator stats
3. 7/30/90 day dynamics

## Phase 7: Notifications

1. notification settings
2. basic notifications

---

# 20. What Cursor Should Prioritize

1. Keep architecture simple.
2. Avoid overengineering.
3. Use services and repositories.
4. Keep AI provider replaceable.
5. Store all core data from day one.
6. Do not implement profiles, badges, clustering, or vector search in MVP.
7. Make lента оценки событий the primary UX path.
8. Make event deletion and anonymization correct.
9. Make repeated event display impossible.
10. Make rating recalculation deterministic.
