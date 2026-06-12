"""Canonical admin_event_log event names and UI groupings."""

from dataclasses import dataclass


@dataclass(frozen=True)
class EventMeta:
    name: str
    label: str
    group: str


EVENT_GROUPS: dict[str, str] = {
    "user": "Пользователь",
    "events": "События",
    "feed": "Лента",
    "friends": "Друзья",
    "notifications": "Уведомления",
    "ai": "AI",
    "settings": "Настройки",
}

# All tracked user/system actions in v1.
EVENT_CATALOG: tuple[EventMeta, ...] = (
    EventMeta("user_registered", "Регистрация", "user"),
    EventMeta("user_seen", "Активность в боте", "user"),
    EventMeta("event_created", "Создание события", "events"),
    EventMeta("event_deleted", "Удаление события", "events"),
    EventMeta("event_rated", "Оценка события", "events"),
    EventMeta("event_skipped", "Пропуск события", "events"),
    EventMeta("feed_started", "Старт ленты", "feed"),
    EventMeta("feed_empty", "Пустая лента", "feed"),
    EventMeta("batch_created", "Создан батч", "feed"),
    EventMeta("batch_completed", "Батч завершён", "feed"),
    EventMeta("event_shown", "Показ события", "feed"),
    EventMeta("event_injected_into_batch", "Injection в батч", "feed"),
    EventMeta("friend_invite_sent", "Отправка инвайта", "friends"),
    EventMeta("friendship_accepted", "Дружба принята", "friends"),
    EventMeta("friendship_rejected", "Дружба отклонена", "friends"),
    EventMeta("notification_created", "Уведомление создано", "notifications"),
    EventMeta("notification_sent", "Уведомление отправлено", "notifications"),
    EventMeta("notification_failed", "Ошибка уведомления", "notifications"),
    EventMeta("ai_generation_triggered", "AI: запуск генерации", "ai"),
    EventMeta("ai_generation_completed", "AI: генерация OK", "ai"),
    EventMeta("ai_generation_failed", "AI: ошибка генерации", "ai"),
    EventMeta("settings_notifications_changed", "Смена уведомлений", "settings"),
    EventMeta("settings_language_changed", "Смена языка контента", "settings"),
)

EVENT_NAMES: frozenset[str] = frozenset(e.name for e in EVENT_CATALOG)

EVENT_LABELS: dict[str, str] = {e.name: e.label for e in EVENT_CATALOG}

GROUP_EVENT_NAMES: dict[str, list[str]] = {}
for _meta in EVENT_CATALOG:
    GROUP_EVENT_NAMES.setdefault(_meta.group, []).append(_meta.name)

# Routine pings hidden by default on Activity page.
NOISY_EVENT_NAMES: frozenset[str] = frozenset({"user_seen", "event_shown"})
