from typing import Any


def resolve_lang(language_code: str | None, default: str = "en") -> str:
    if not language_code:
        return default
    return "ru" if language_code.lower().startswith("ru") else "en"


MESSAGES: dict[str, dict[str, str]] = {
    "welcome": {
        "ru": (
            "Добро пожаловать в LifeLedger.\n\n"
            "Здесь люди оценивают жизненные события и моральные ситуации.\n\n"
            "Вы можете:\n"
            "— оценивать события других людей;\n"
            "— добавлять свои события;\n"
            "— сравнивать свою оценку с оценкой сообщества.\n\n"
            "Начнем с первого события."
        ),
        "en": (
            "Welcome to LifeLedger.\n\n"
            "People rate life events and moral situations here.\n\n"
            "You can:\n"
            "— rate other people's events;\n"
            "— add your own events;\n"
            "— compare your score with the community.\n\n"
            "Let's start with your first event."
        ),
    },
    "batch_prepared": {
        "ru": "Для вас подготовлено {count} событий.",
        "en": "{count} events are ready for you.",
    },
    "no_events": {
        "ru": (
            "Пока нет новых событий для оценки.\n\n"
            "➕ Добавьте свое событие — /add\n"
            "📊 Посмотреть статистику"
        ),
        "en": (
            "No new events to rate right now.\n\n"
            "➕ Add your event — /add\n"
            "📊 View stats"
        ),
    },
    "add_choose_type": {
        "ru": "Какой тип события вы хотите добавить?",
        "en": "What type of event do you want to add?",
    },
    "add_enter_text": {
        "ru": (
            "Опишите событие.\n\n"
            "Можно писать на любом языке.\n"
            "Постарайтесь добавить контекст, если он важен для оценки."
        ),
        "en": (
            "Describe the event.\n\n"
            "You can write in any language.\n"
            "Add context if it matters for rating."
        ),
    },
    "add_enter_text_hypothetical": {
        "ru": (
            "Опишите гипотетическую ситуацию и какой выбор сделал человек.\n\n"
            "Нужно конкретное действие, а не вопрос «что бы вы сделали».\n\n"
            "Пример: «предпочёл спасти пятерых незнакомцев, а не своего сына».\n"
            "Пример: «предпочёл спасти невесту, а не пятерых незнакомцев»."
        ),
        "en": (
            "Describe the hypothetical situation and the choice the person made.\n\n"
            "State a concrete action, not an open \"what would you do\" question.\n\n"
            "Example: \"chose to save five strangers instead of their son\".\n"
            "Example: \"chose to save their fiancée instead of five strangers\"."
        ),
    },
    "add_self_score": {
        "ru": "Как вы сами оцениваете это событие?",
        "en": "How do you rate this event yourself?",
    },
    "add_processing": {
        "ru": "Обрабатываем событие…",
        "en": "Processing your event…",
    },
    "add_cancelled": {
        "ru": "Добавление события отменено.",
        "en": "Event creation cancelled.",
    },
    "add_text_empty": {
        "ru": "Текст не может быть пустым. Опишите событие.",
        "en": "Text cannot be empty. Please describe the event.",
    },
    "my_events_empty": {
        "ru": "У вас пока нет событий.\n\nДобавьте первое — /add",
        "en": "You have no events yet.\n\nAdd your first one — /add",
    },
    "my_events_title": {
        "ru": "Мои события",
        "en": "My events",
    },
    "delete_confirm": {
        "ru": (
            "Удалить событие?\n\n"
            "Оно исчезнет из ваших рейтингов и больше не будет показываться другим пользователям."
        ),
        "en": (
            "Delete this event?\n\n"
            "It will be removed from your ratings and will no longer be shown to others."
        ),
    },
    "event_deleted": {
        "ru": "Событие удалено.",
        "en": "Event deleted.",
    },
    "event_not_found": {
        "ru": "Это событие больше недоступно.",
        "en": "This event is no longer available.",
    },
    "event_type_real": {
        "ru": "Реальное событие",
        "en": "Real event",
    },
    "event_type_hypothetical": {
        "ru": "Гипотетическая ситуация",
        "en": "Hypothetical situation",
    },
    "rate_prompt": {
        "ru": "Как вы оцениваете это событие?",
        "en": "How do you rate this event?",
    },
    "your_score": {
        "ru": "Ваша оценка: {score}",
        "en": "Your score: {score}",
    },
    "community_score": {
        "ru": "Оценка сообщества: {score}",
        "en": "Community score: {score}",
    },
    "skipped": {
        "ru": "Событие пропущено.",
        "en": "Event skipped.",
    },
    "batch_complete": {
        "ru": (
            "Вы завершили текущую подборку.\n\n"
            "Хотите получить еще {size} событий?"
        ),
        "en": (
            "You finished this batch.\n\n"
            "Get {size} more events?"
        ),
    },
    "already_rated": {
        "ru": "Вы уже оценивали это событие.",
        "en": "You already rated this event.",
    },
    "own_event": {
        "ru": "Вы не можете оценивать собственное событие.",
        "en": "You cannot rate your own event.",
    },
    "coming_soon": {
        "ru": "Этот раздел появится в следующих обновлениях.",
        "en": "This section is coming in a future update.",
    },
    "friends_screen": {
        "ru": (
            "Ваши друзья: {count}\n\n"
            "Пригласите друга, чтобы получать больше оценок от своего круга общения."
        ),
        "en": (
            "Your friends: {count}\n\n"
            "Invite a friend to get more ratings from your circle."
        ),
    },
    "friends_invite_link": {
        "ru": "Ваша ссылка для приглашения:\n\n{link}",
        "en": "Your invite link:\n\n{link}",
    },
    "friends_invite_prompt": {
        "ru": (
            "Пользователь приглашает вас стать друзьями в LifeLedger.\n\n"
            "Дружба позволит вашим событиям попадать в подборки друг друга, "
            "но автор событий останется анонимным.\n\n"
            "Подтвердить дружбу?"
        ),
        "en": (
            "Someone invited you to become friends on LifeLedger.\n\n"
            "Friendship lets your events appear in each other's feeds, "
            "but event authors stay anonymous.\n\n"
            "Accept friendship?"
        ),
    },
    "friends_accepted": {
        "ru": "Дружба подтверждена.",
        "en": "Friendship confirmed.",
    },
    "friends_rejected": {
        "ru": "Приглашение отклонено.",
        "en": "Invitation declined.",
    },
    "friends_already": {
        "ru": "Вы уже друзья.",
        "en": "You are already friends.",
    },
    "friends_self_invite": {
        "ru": "Нельзя пригласить самого себя.",
        "en": "You cannot invite yourself.",
    },
    "friends_invalid_link": {
        "ru": "Ссылка приглашения недействительна.",
        "en": "This invite link is invalid.",
    },
    "friends_incoming_empty": {
        "ru": "Нет входящих приглашений.",
        "en": "No incoming invitations.",
    },
    "friends_incoming_title": {
        "ru": "Входящие приглашения: {count}",
        "en": "Incoming invitations: {count}",
    },
    "friends_incoming_item": {
        "ru": "Приглашение {n}",
        "en": "Invitation {n}",
    },
    "friends_share_text": {
        "ru": "Присоединяйся ко мне в LifeLedger — оцениваем жизненные события вместе:",
        "en": "Join me on LifeLedger — let's rate life events together:",
    },
    "stats_author_title": {
        "ru": "Мои события",
        "en": "My events",
    },
    "stats_rating_title": {
        "ru": "Рейтинг:",
        "en": "Rating:",
    },
    "stats_average_title": {
        "ru": "Средняя оценка:",
        "en": "Average score:",
    },
    "stats_dynamics_title": {
        "ru": "Динамика рейтинга:",
        "en": "Rating dynamics:",
    },
    "stats_evaluator_title": {
        "ru": "Мои оценки",
        "en": "My ratings",
    },
    "stats_rated_count": {
        "ru": "Оценено событий: {count}",
        "en": "Events rated: {count}",
    },
    "stats_you_rated": {
        "ru": "Вы оценивали: {score}",
        "en": "You rated: {score}",
    },
    "stats_community_rated": {
        "ru": "Оценивало сообщество: {score}",
        "en": "Community rated: {score}",
    },
    "stats_deviation": {
        "ru": "Отклонение: {score}",
        "en": "Deviation: {score}",
    },
    "settings_title": {
        "ru": "Настройки",
        "en": "Settings",
    },
    "settings_notifications_on": {
        "ru": "Уведомления: включены",
        "en": "Notifications: enabled",
    },
    "settings_notifications_off": {
        "ru": "Уведомления: отключены",
        "en": "Notifications: disabled",
    },
    "settings_notifications_enabled": {
        "ru": "Уведомления включены",
        "en": "Notifications enabled",
    },
    "settings_notifications_disabled": {
        "ru": "Уведомления отключены",
        "en": "Notifications disabled",
    },
    "settings_content_language": {
        "ru": "Язык событий: {language}",
        "en": "Event language: {language}",
    },
    "settings_ui_language_hint": {
        "ru": "Язык кнопок и меню — из настроек Telegram.",
        "en": "Button and menu language follows your Telegram settings.",
    },
    "settings_pick_language": {
        "ru": "Выберите язык, на котором показывать события:",
        "en": "Choose the language for displaying events:",
    },
    "settings_content_language_changed": {
        "ru": "Язык событий изменён",
        "en": "Event language changed",
    },
    "notify_new_ratings": {
        "ru": "Ваше событие получило новые оценки.",
        "en": "Your event received new ratings.",
    },
    "notify_first_friend_rating": {
        "ru": "Ваше событие впервые оценили друзья.",
        "en": "Friends rated your event for the first time.",
    },
    "error_generic": {
        "ru": "Произошла ошибка. Попробуйте еще раз.",
        "en": "Something went wrong. Please try again.",
    },
}


def t(key: str, lang: str, **kwargs: Any) -> str:
    block = MESSAGES[key]
    text = block.get(lang) or block["en"]
    return text.format(**kwargs) if kwargs else text
