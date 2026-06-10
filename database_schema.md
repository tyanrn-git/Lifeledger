# LifeLedger MVP v1.0 — Database Schema

Файл: `database_schema.md`  
Назначение: описание структуры базы данных для MVP Telegram-бота LifeLedger.  
Рекомендуемая БД: **Supabase PostgreSQL**.

---

# 1. Общие принципы модели данных

LifeLedger хранит:

1. Пользователей Telegram.
2. События пользователей.
3. Самооценку события.
4. Оценки друзей.
5. Оценки сообщества.
6. Первичную AI-оценку события.
7. Переводы событий.
8. Историю показов событий оценщикам.
9. Дружеские связи.
10. Снимки рейтингов и средних оценок пользователя.

Ключевые принципы:

- пользователь может быть и автором событий, и оценщиком;
- событие после публикации нельзя редактировать;
- событие можно удалить;
- после удаления связь события с пользователем удаляется или обезличивается;
- одно событие не должно показываться одному оценщику более одного раза;
- автор не может оценивать свое событие как обычный оценщик;
- дружба двусторонняя и требует подтверждения;
- рейтинг и средняя оценка — разные показатели;
- оценки друзей и оценки сообщества считаются отдельно;
- оценка сообщества на старте может включать AI Score;
- по мере накопления оценок пользователей вес AI Score уменьшается.

---

# 2. Рекомендуемые PostgreSQL extensions

```sql
create extension if not exists "uuid-ossp";
create extension if not exists "pgcrypto";
```

Для MVP векторное расширение `pgvector` не требуется.

---

# 3. ENUM types

## 3.1. event_type

```sql
create type event_type as enum (
  'real',
  'hypothetical'
);
```

- `real` — реальное событие.
- `hypothetical` — гипотетическая моральная дилемма.

## 3.2. rating_scope

```sql
create type rating_scope as enum (
  'friend',
  'community'
);
```

- `friend` — оценка от друга автора.
- `community` — оценка от пользователя сообщества.

## 3.3. friendship_status

```sql
create type friendship_status as enum (
  'pending',
  'accepted',
  'rejected',
  'blocked'
);
```

- `pending` — приглашение отправлено, но дружба еще не подтверждена.
- `accepted` — дружба подтверждена.
- `rejected` — приглашение отклонено.
- `blocked` — пользователь заблокировал дружбу.

## 3.4. impression_status

```sql
create type impression_status as enum (
  'shown',
  'rated',
  'skipped'
);
```

- `shown` — событие было показано пользователю.
- `rated` — пользователь оценил событие.
- `skipped` — пользователь пропустил событие.

## 3.5. notification_type

```sql
create type notification_type as enum (
  'new_ratings',
  'first_friend_rating',
  'community_score_changed'
);
```

---

# 4. Таблица users

Хранит пользователей Telegram.

```sql
create table users (
  id uuid primary key default gen_random_uuid(),

  telegram_id bigint not null unique,
  username text,
  first_name text,
  last_name text,

  language_code text not null default 'en',

  notifications_enabled boolean not null default true,

  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  last_seen_at timestamptz
);
```

## Поля

| Поле | Тип | Назначение |
|---|---|---|
| id | uuid | внутренний ID пользователя |
| telegram_id | bigint | Telegram ID |
| username | text | Telegram username |
| first_name | text | имя из Telegram |
| last_name | text | фамилия из Telegram |
| language_code | text | язык интерфейса Telegram |
| notifications_enabled | boolean | включены ли уведомления |
| created_at | timestamptz | дата регистрации |
| updated_at | timestamptz | дата обновления |
| last_seen_at | timestamptz | последняя активность |

## Индексы

```sql
create index idx_users_language_code on users(language_code);
create index idx_users_last_seen_at on users(last_seen_at);
```

---

# 5. Таблица events

Хранит события пользователей.

```sql
create table events (
  id uuid primary key default gen_random_uuid(),

  author_user_id uuid references users(id) on delete set null,

  event_type event_type not null,

  original_text text not null,
  original_language text not null,

  event_time timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),

  action_text text,
  context_text text,
  category text,
  normalized_text text,

  self_score integer not null check (self_score between -10 and 10),

  ai_score numeric(5,2),
  community_user_score numeric(5,2),
  final_community_score numeric(5,2),

  friends_score numeric(5,2),

  friends_ratings_count integer not null default 0,
  community_ratings_count integer not null default 0,

  is_deleted boolean not null default false,
  deleted_at timestamptz,

  anonymized_after_delete boolean not null default false
);
```

## Поля

| Поле | Тип | Назначение |
|---|---|---|
| id | uuid | ID события |
| author_user_id | uuid | автор события; после удаления может быть NULL |
| event_type | enum | real / hypothetical |
| original_text | text | исходный текст пользователя |
| original_language | text | язык исходного текста |
| event_time | timestamptz | время события, если указано; иначе можно использовать created_at |
| created_at | timestamptz | дата публикации |
| updated_at | timestamptz | дата обновления расчетных полей |
| action_text | text | выделенное действие |
| context_text | text | выделенный контекст |
| category | text | категория, определенная ИИ |
| normalized_text | text | нормализованная версия для показа/перевода |
| self_score | integer | оценка автора от -10 до +10 |
| ai_score | numeric | стартовая AI-оценка |
| community_user_score | numeric | средняя оценка пользователей сообщества |
| final_community_score | numeric | итоговая оценка сообщества |
| friends_score | numeric | средняя оценка друзей |
| friends_ratings_count | integer | количество оценок друзей |
| community_ratings_count | integer | количество оценок сообщества |
| is_deleted | boolean | удалено ли событие |
| deleted_at | timestamptz | дата удаления |
| anonymized_after_delete | boolean | была ли удалена связь с пользователем |

## Индексы

```sql
create index idx_events_author_user_id on events(author_user_id);
create index idx_events_event_type on events(event_type);
create index idx_events_created_at on events(created_at);
create index idx_events_event_time on events(event_time);
create index idx_events_category on events(category);
create index idx_events_is_deleted on events(is_deleted);
create index idx_events_community_ratings_count on events(community_ratings_count);
create index idx_events_friends_ratings_count on events(friends_ratings_count);
```

## Важные правила

1. `self_score` обязателен.
2. `ai_score` желательно рассчитывать сразу после создания события.
3. `final_community_score` на старте может быть равен `ai_score`.
4. После удаления события:
   - `is_deleted = true`;
   - `deleted_at = now()`;
   - `author_user_id = null`;
   - `anonymized_after_delete = true`;
   - событие не показывается новым оценщикам;
   - событие не участвует в рейтингах автора.

---

# 6. Таблица event_translations

Хранит переводы нормализованного текста события.

```sql
create table event_translations (
  id uuid primary key default gen_random_uuid(),

  event_id uuid not null references events(id) on delete cascade,

  language_code text not null,
  translated_text text not null,

  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),

  unique(event_id, language_code)
);
```

## Поля

| Поле | Тип | Назначение |
|---|---|---|
| event_id | uuid | событие |
| language_code | text | язык перевода |
| translated_text | text | переведенный нормализованный текст |

## Индексы

```sql
create index idx_event_translations_event_id on event_translations(event_id);
create index idx_event_translations_language_code on event_translations(language_code);
```

## Логика

Когда событие нужно показать оценщику:

1. Определить язык оценщика `users.language_code`.
2. Проверить наличие перевода в `event_translations`.
3. Если перевод есть — показать его.
4. Если перевода нет — создать через AI, сохранить и показать.

---

# 7. Таблица friendships

Хранит дружеские связи.

Дружба требует подтверждения и считается двусторонней.

```sql
create table friendships (
  id uuid primary key default gen_random_uuid(),

  requester_user_id uuid not null references users(id) on delete cascade,
  addressee_user_id uuid not null references users(id) on delete cascade,

  status friendship_status not null default 'pending',

  created_at timestamptz not null default now(),
  responded_at timestamptz,

  constraint no_self_friendship check (requester_user_id <> addressee_user_id),

  unique(requester_user_id, addressee_user_id)
);
```

## Поля

| Поле | Тип | Назначение |
|---|---|---|
| requester_user_id | uuid | кто отправил приглашение |
| addressee_user_id | uuid | кто получил приглашение |
| status | enum | pending / accepted / rejected / blocked |
| responded_at | timestamptz | дата ответа |

## Индексы

```sql
create index idx_friendships_requester on friendships(requester_user_id);
create index idx_friendships_addressee on friendships(addressee_user_id);
create index idx_friendships_status on friendships(status);
```

## Логика

Пользователь А отправляет ссылку.

Пользователь Б регистрируется по ссылке.

Создается friendship:

- requester_user_id = A
- addressee_user_id = B
- status = pending

После подтверждения Б:

- status = accepted
- responded_at = now()

Для поиска друзей пользователя нужно учитывать обе стороны связи.

---

# 8. Таблица ratings

Хранит оценки событий другими пользователями.

```sql
create table ratings (
  id uuid primary key default gen_random_uuid(),

  event_id uuid not null references events(id) on delete cascade,
  rater_user_id uuid not null references users(id) on delete cascade,

  rating_scope rating_scope not null,

  score integer not null check (score between -10 and 10),

  created_at timestamptz not null default now(),

  unique(event_id, rater_user_id)
);
```

## Поля

| Поле | Тип | Назначение |
|---|---|---|
| event_id | uuid | оцениваемое событие |
| rater_user_id | uuid | оценщик |
| rating_scope | enum | friend / community |
| score | integer | оценка от -10 до +10 |
| created_at | timestamptz | дата оценки |

## Индексы

```sql
create index idx_ratings_event_id on ratings(event_id);
create index idx_ratings_rater_user_id on ratings(rater_user_id);
create index idx_ratings_scope on ratings(rating_scope);
create index idx_ratings_created_at on ratings(created_at);
```

## Правила

1. Один пользователь может оценить событие только один раз.
2. Автор не должен оценивать собственное событие через `ratings`.
3. Самооценка автора хранится в `events.self_score`.
4. Если оценщик является подтвержденным другом автора события, `rating_scope = friend`.
5. Иначе `rating_scope = community`.

---

# 9. Таблица event_impressions

Хранит историю показов событий пользователям.

Нужна, чтобы не показывать одно событие одному пользователю повторно.

```sql
create table event_impressions (
  id uuid primary key default gen_random_uuid(),

  event_id uuid not null references events(id) on delete cascade,
  user_id uuid not null references users(id) on delete cascade,

  status impression_status not null default 'shown',

  source_priority integer,
  batch_id uuid,

  shown_at timestamptz not null default now(),
  rated_at timestamptz,
  skipped_at timestamptz,

  unique(event_id, user_id)
);
```

## Поля

| Поле | Тип | Назначение |
|---|---|---|
| event_id | uuid | событие |
| user_id | uuid | пользователь, которому показали событие |
| status | enum | shown / rated / skipped |
| source_priority | integer | приоритет, по которому событие попало в подборку |
| batch_id | uuid | ID подборки |
| shown_at | timestamptz | когда показано |
| rated_at | timestamptz | когда оценено |
| skipped_at | timestamptz | когда пропущено |

## Индексы

```sql
create index idx_event_impressions_user_id on event_impressions(user_id);
create index idx_event_impressions_event_id on event_impressions(event_id);
create index idx_event_impressions_status on event_impressions(status);
create index idx_event_impressions_batch_id on event_impressions(batch_id);
```

## Логика

Если событие было:

- показано;
- оценено;
- пропущено;

оно больше не попадает в подборки этого пользователя.

---

# 10. Таблица rating_batches

Хранит подборки событий для оценки.

```sql
create table rating_batches (
  id uuid primary key default gen_random_uuid(),

  user_id uuid not null references users(id) on delete cascade,

  created_at timestamptz not null default now(),
  completed_at timestamptz,

  requested_size integer not null default 30,
  actual_size integer not null default 0
);
```

## Поля

| Поле | Тип | Назначение |
|---|---|---|
| user_id | uuid | пользователь, для которого создана подборка |
| requested_size | integer | запрошенный размер, обычно 30 |
| actual_size | integer | фактическое количество событий |
| completed_at | timestamptz | когда подборка завершена |

## Индексы

```sql
create index idx_rating_batches_user_id on rating_batches(user_id);
create index idx_rating_batches_created_at on rating_batches(created_at);
```

## Логика

Пользователь открывает ленту оценки.

Система формирует подборку до 30 событий.

Если события закончились, пользователь может запросить еще одну подборку.

---

# 11. Таблица user_rating_snapshots

Хранит снимки рейтингов и средних оценок пользователя.

```sql
create table user_rating_snapshots (
  id uuid primary key default gen_random_uuid(),

  user_id uuid not null references users(id) on delete cascade,

  period_start timestamptz,
  period_end timestamptz,

  self_rating_total numeric(10,2) not null default 0,
  friends_rating_total numeric(10,2) not null default 0,
  community_rating_total numeric(10,2) not null default 0,

  self_average_score numeric(5,2),
  friends_average_score numeric(5,2),
  community_average_score numeric(5,2),

  authored_events_count integer not null default 0,
  events_with_friend_scores_count integer not null default 0,
  events_with_community_scores_count integer not null default 0,

  created_at timestamptz not null default now()
);
```

## Поля

| Поле | Тип | Назначение |
|---|---|---|
| user_id | uuid | пользователь |
| period_start | timestamptz | начало периода |
| period_end | timestamptz | конец периода |
| self_rating_total | numeric | сумма самооценок |
| friends_rating_total | numeric | сумма оценок друзей |
| community_rating_total | numeric | сумма оценок сообщества |
| self_average_score | numeric | средняя самооценка |
| friends_average_score | numeric | средняя оценка друзей |
| community_average_score | numeric | средняя оценка сообщества |

## Индексы

```sql
create index idx_user_rating_snapshots_user_id on user_rating_snapshots(user_id);
create index idx_user_rating_snapshots_period on user_rating_snapshots(period_start, period_end);
```

## Логика

Используется для отображения:

- рейтинга за все время;
- рейтинга за 7 дней;
- рейтинга за 30 дней;
- рейтинга за 90 дней;
- динамики рейтинга.

---

# 12. Таблица evaluator_stats

Хранит статистику пользователя как оценщика.

```sql
create table evaluator_stats (
  id uuid primary key default gen_random_uuid(),

  user_id uuid not null references users(id) on delete cascade,

  period_start timestamptz,
  period_end timestamptz,

  rated_events_count integer not null default 0,

  user_average_given_score numeric(5,2),
  community_average_for_same_events numeric(5,2),
  deviation_from_community numeric(5,2),

  created_at timestamptz not null default now()
);
```

## Поля

| Поле | Тип | Назначение |
|---|---|---|
| rated_events_count | integer | сколько событий пользователь оценил |
| user_average_given_score | numeric | средняя оценка пользователя |
| community_average_for_same_events | numeric | средняя оценка сообщества по тем же событиям |
| deviation_from_community | numeric | разница |

## Формула

```text
deviation_from_community =
user_average_given_score
-
community_average_for_same_events
```

## Индексы

```sql
create index idx_evaluator_stats_user_id on evaluator_stats(user_id);
create index idx_evaluator_stats_period on evaluator_stats(period_start, period_end);
```

---

# 13. Таблица notifications

Хранит уведомления.

```sql
create table notifications (
  id uuid primary key default gen_random_uuid(),

  user_id uuid not null references users(id) on delete cascade,
  event_id uuid references events(id) on delete cascade,

  notification_type notification_type not null,

  title text,
  body text,

  is_sent boolean not null default false,
  sent_at timestamptz,

  created_at timestamptz not null default now()
);
```

## Индексы

```sql
create index idx_notifications_user_id on notifications(user_id);
create index idx_notifications_is_sent on notifications(is_sent);
create index idx_notifications_created_at on notifications(created_at);
```

## Типы уведомлений

- новые оценки события;
- первая оценка друзей;
- существенное изменение оценки сообщества.

---

# 14. Логика расчета рейтингов

## 14.1. Рейтинг

Рейтинг = сумма оценок.

Для автора считаются три рейтинга:

```text
self_rating_total = сумма self_score по активным событиям автора

friends_rating_total = сумма friends_score по активным событиям автора,
где friends_score не NULL

community_rating_total = сумма final_community_score по активным событиям автора
```

Удаленные события не учитываются.

## 14.2. Средняя оценка

Средняя оценка = среднее арифметическое.

```text
self_average_score =
avg(self_score)

friends_average_score =
avg(friends_score), только события где friends_score не NULL

community_average_score =
avg(final_community_score)
```

## 14.3. Периоды

Нужно поддержать:

- все время;
- последние 7 дней;
- последние 30 дней;
- последние 90 дней.

Для периода использовать `event_time`, если он есть.

Если `event_time` отсутствует, использовать `created_at`.

---

# 15. Логика пересчета оценки события

После создания события:

1. AI рассчитывает `ai_score`.
2. `final_community_score = ai_score`.
3. `community_ratings_count = 0`.
4. `friends_ratings_count = 0`.
5. `friends_score = null`.

После новой оценки:

1. Проверить, является ли оценщик другом автора.
2. Создать запись в `ratings`.
3. Обновить `event_impressions.status = rated`.
4. Пересчитать:
   - friends_score;
   - community_user_score;
   - final_community_score;
   - friends_ratings_count;
   - community_ratings_count.
5. Пересчитать или пометить к пересчету статистику автора.
6. Пересчитать или пометить к пересчету статистику оценщика.

---

# 16. Логика определения rating_scope

Для события `E` и оценщика `U`:

1. Найти автора события `A`.
2. Если `U = A`, не разрешать оценку.
3. Если между `U` и `A` есть accepted friendship:
   - rating_scope = friend.
4. Иначе:
   - rating_scope = community.

---

# 17. Алгоритм формирования подборки событий

Размер подборки:

```text
batch_size = 30
```

Подборка не является дневным лимитом.

Пользователь может запрашивать новые подборки.

## 17.1. Исключить

Не показывать:

- удаленные события;
- события самого пользователя;
- события, которые пользователь уже видел;
- события, которые пользователь уже оценил;
- события, которые пользователь пропустил.

## 17.2. Приоритеты

### Приоритет 1: события друзей

События авторов, с которыми есть accepted friendship.

### Приоритет 2: новые события сообщества

Свежие события, которым нужны первые оценки.

### Приоритет 3: события с малым количеством оценок

События с низким `community_ratings_count`.

## 17.3. Перемешивание

После отбора события перемешиваются.

Пользователь не должен видеть, является ли событие событием друга или сообщества.

---

# 18. Удаление и обезличивание

При удалении события автором:

```sql
update events
set
  is_deleted = true,
  deleted_at = now(),
  author_user_id = null,
  anonymized_after_delete = true
where id = :event_id
  and author_user_id = :current_user_id;
```

После удаления:

- событие не показывается новым пользователям;
- событие исключается из рейтингов автора;
- связь с автором удаляется;
- обезличенные данные могут остаться для аналитики.

---

# 19. Рекомендуемые SQL-представления

## 19.1. active_events

```sql
create view active_events as
select *
from events
where is_deleted = false;
```

## 19.2. accepted_friendships

```sql
create view accepted_friendships as
select requester_user_id as user_id, addressee_user_id as friend_user_id
from friendships
where status = 'accepted'
union
select addressee_user_id as user_id, requester_user_id as friend_user_id
from friendships
where status = 'accepted';
```

---

# 20. Ограничения целостности

Обязательные правила на уровне приложения:

1. Автор не может оценить свое событие.
2. Пользователь не может оценить событие дважды.
3. Пользователь не может повторно увидеть событие.
4. Удаленные события не показываются.
5. Удаленные события не входят в рейтинги автора.
6. Дружба должна быть подтвержденной.
7. События друзей и сообщества перемешиваются в подборке.
8. Оценка друзей считается только по фактически проголосовавшим друзьям.
9. Если оценок друзей нет, отображается `—`, а не `0`.

---

# 21. Примечания для Cursor

Cursor должен реализовывать проект так, чтобы:

- схема БД не мешала будущему построению профилей пользователей;
- оценки чужих событий сохранялись максимально полно;
- данные оценщика можно было использовать для будущего профиля;
- Action / Context / Category сохранялись с первого дня;
- перевод сохранялся в БД и не генерировался повторно без необходимости;
- алгоритм весов AI/User можно было менять без миграции БД;
- удаление события не уничтожало обезличенную аналитическую ценность, но удаляло связь с пользователем.

---

# 22. Минимальный порядок реализации БД

1. users
2. events
3. friendships
4. ratings
5. event_impressions
6. event_translations
7. rating_batches
8. user_rating_snapshots
9. evaluator_stats
10. notifications

---

# 23. Минимальный набор функций поверх БД

1. Создать или обновить пользователя Telegram.
2. Создать событие.
3. Получить событие для оценки.
4. Создать подборку из 30 событий.
5. Оценить событие.
6. Пропустить событие.
7. Пересчитать оценки события.
8. Пересчитать статистику автора.
9. Пересчитать статистику оценщика.
10. Отправить приглашение в друзья.
11. Подтвердить дружбу.
12. Удалить событие с обезличиванием.
13. Получить статистику пользователя.
14. Получить список событий пользователя.
