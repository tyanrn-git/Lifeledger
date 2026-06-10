from collections.abc import Sequence
from uuid import UUID

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    KeyboardButtonRequestUsers,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)

from app.schemas.events import Event


def _score_label(score: int) -> str:
    if score > 0:
        return f"+{score}"
    return str(score)


def _action_row(lang: str, event_id: UUID) -> list[InlineKeyboardButton]:
    skip_label = "⏭ Пропустить" if lang == "ru" else "⏭ Skip"
    add_label = "➕" if lang == "ru" else "➕ Add"
    stats_label = "📊" if lang == "ru" else "📊 Stats"
    return [
        InlineKeyboardButton(text=skip_label, callback_data=f"skip:{event_id}"),
        InlineKeyboardButton(text=add_label, callback_data="nav:add"),
        InlineKeyboardButton(text=stats_label, callback_data="nav:stats"),
    ]


def _score_rows(callback_builder) -> list[list[InlineKeyboardButton]]:
    scores = list(range(-10, 11))
    return [
        [
            InlineKeyboardButton(text=_score_label(s), callback_data=callback_builder(s))
            for s in scores[i : i + 7]
        ]
        for i in range(0, len(scores), 7)
    ]


def rating_keyboard(event_id: UUID, lang: str) -> InlineKeyboardMarkup:
    score_rows = _score_rows(lambda s: f"rate:{event_id}:{s}")
    return InlineKeyboardMarkup(inline_keyboard=[*score_rows, _action_row(lang, event_id)])


def self_score_keyboard(lang: str) -> InlineKeyboardMarkup:
    cancel = "Отмена" if lang == "ru" else "Cancel"
    score_rows = _score_rows(lambda s: f"add_score:{s}")
    score_rows.append([InlineKeyboardButton(text=cancel, callback_data="add_cancel")])
    return InlineKeyboardMarkup(inline_keyboard=score_rows)


def event_type_keyboard(lang: str) -> InlineKeyboardMarkup:
    if lang == "ru":
        real_label = "Реальное событие"
        hyp_label = "Гипотетическая ситуация"
        cancel = "Отмена"
    else:
        real_label = "Real event"
        hyp_label = "Hypothetical situation"
        cancel = "Cancel"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=real_label, callback_data="add_type:real")],
            [InlineKeyboardButton(text=hyp_label, callback_data="add_type:hypothetical")],
            [InlineKeyboardButton(text=cancel, callback_data="add_cancel")],
        ]
    )


def after_add_keyboard(lang: str) -> InlineKeyboardMarkup:
    rate_label = "⭐ Оценить события" if lang == "ru" else "⭐ Rate events"
    events_label = "📖 Мои события" if lang == "ru" else "📖 My events"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=rate_label, callback_data="nav:rate"),
                InlineKeyboardButton(text=events_label, callback_data="nav:events"),
            ],
        ]
    )


def events_list_keyboard(events: Sequence[Event], lang: str) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for i, event in enumerate(events, start=1):
        preview = event.normalized_text.replace("\n", " ")
        if len(preview) > 40:
            preview = preview[:37] + "..."
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"{i}. {preview}",
                    callback_data=f"event_open:{event.id}",
                )
            ]
        )
    add_label = "➕ Добавить событие" if lang == "ru" else "➕ Add event"
    rows.append([InlineKeyboardButton(text=add_label, callback_data="nav:add")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def event_detail_keyboard(event_id: UUID, lang: str) -> InlineKeyboardMarkup:
    delete_label = "Удалить событие" if lang == "ru" else "Delete event"
    back_label = "Назад" if lang == "ru" else "Back"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=delete_label, callback_data=f"event_delete:{event_id}")],
            [InlineKeyboardButton(text=back_label, callback_data="nav:events")],
        ]
    )


def delete_confirm_keyboard(event_id: UUID, lang: str) -> InlineKeyboardMarkup:
    yes_label = "Да, удалить" if lang == "ru" else "Yes, delete"
    no_label = "Отмена" if lang == "ru" else "Cancel"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=yes_label, callback_data=f"event_delete_confirm:{event_id}"),
                InlineKeyboardButton(text=no_label, callback_data=f"event_open:{event_id}"),
            ],
        ]
    )


def next_event_keyboard(lang: str, batch_id: UUID) -> InlineKeyboardMarkup:
    label = "Следующее событие →" if lang == "ru" else "Next event →"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=label, callback_data=f"feed:next:{batch_id}")],
        ]
    )


def batch_complete_keyboard(lang: str, batch_size: int) -> InlineKeyboardMarkup:
    if lang == "ru":
        new_batch = f"Получить еще {batch_size}"
        add_label = "➕ Добавить событие"
        stats_label = "📊 Статистика"
    else:
        new_batch = f"Get {batch_size} more"
        add_label = "➕ Add event"
        stats_label = "📊 Stats"

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=new_batch, callback_data="feed:new_batch")],
            [
                InlineKeyboardButton(text=add_label, callback_data="nav:add"),
                InlineKeyboardButton(text=stats_label, callback_data="nav:stats"),
            ],
        ]
    )


def settings_keyboard(enabled: bool, lang: str) -> InlineKeyboardMarkup:
    if lang == "ru":
        enable_label = "Включить уведомления"
        disable_label = "Отключить уведомления"
        language_label = "Язык событий"
    else:
        enable_label = "Enable notifications"
        disable_label = "Disable notifications"
        language_label = "Event language"

    notify_row = (
        [InlineKeyboardButton(text=disable_label, callback_data="settings:disable")]
        if enabled
        else [InlineKeyboardButton(text=enable_label, callback_data="settings:enable")]
    )
    return InlineKeyboardMarkup(
        inline_keyboard=[
            notify_row,
            [InlineKeyboardButton(text=language_label, callback_data="settings:lang:page:0")],
        ]
    )


def language_picker_keyboard(
    page: int,
    current_code: str,
    ui_lang: str,
) -> InlineKeyboardMarkup:
    from app.utils.languages import LANGUAGES_PER_PAGE, SUPPORTED_CONTENT_LANGUAGES

    total = len(SUPPORTED_CONTENT_LANGUAGES)
    total_pages = max(1, (total + LANGUAGES_PER_PAGE - 1) // LANGUAGES_PER_PAGE)
    page = max(0, min(page, total_pages - 1))
    start = page * LANGUAGES_PER_PAGE
    chunk = SUPPORTED_CONTENT_LANGUAGES[start : start + LANGUAGES_PER_PAGE]

    rows: list[list[InlineKeyboardButton]] = []
    for option in chunk:
        mark = " ✓" if option.code == current_code else ""
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"{option.native_name}{mark}",
                    callback_data=f"settings:lang:set:{option.code}",
                )
            ]
        )

    nav_row: list[InlineKeyboardButton] = []
    if page > 0:
        prev_label = "◀" if ui_lang == "ru" else "◀ Prev"
        nav_row.append(
            InlineKeyboardButton(text=prev_label, callback_data=f"settings:lang:page:{page - 1}")
        )
    nav_row.append(
        InlineKeyboardButton(text=f"{page + 1}/{total_pages}", callback_data="settings:noop")
    )
    if page < total_pages - 1:
        next_label = "▶" if ui_lang == "ru" else "Next ▶"
        nav_row.append(
            InlineKeyboardButton(text=next_label, callback_data=f"settings:lang:page:{page + 1}")
        )
    rows.append(nav_row)

    back_label = "Назад" if ui_lang == "ru" else "Back"
    rows.append([InlineKeyboardButton(text=back_label, callback_data="settings:main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


FRIENDS_PICK_REQUEST_ID = 1


def friends_pick_user_keyboard(lang: str) -> ReplyKeyboardMarkup:
    pick_label = "👤 Выбрать друга" if lang == "ru" else "👤 Select a friend"
    cancel_label = "✖ Отмена" if lang == "ru" else "✖ Cancel"
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(
                    text=pick_label,
                    request_users=KeyboardButtonRequestUsers(
                        request_id=FRIENDS_PICK_REQUEST_ID,
                        user_is_bot=False,
                        max_quantity=1,
                        request_name=True,
                        request_username=True,
                    ),
                )
            ],
            [KeyboardButton(text=cancel_label)],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def friends_pick_cancel_keyboard() -> ReplyKeyboardRemove:
    return ReplyKeyboardRemove()


def friends_main_keyboard(lang: str, pending_count: int) -> InlineKeyboardMarkup:
    if lang == "ru":
        pick_label = "Пригласить друга"
        invite_label = "Получить ссылку приглашения"
        incoming_label = "Входящие приглашения"
        if pending_count:
            incoming_label = f"Входящие приглашения ({pending_count})"
    else:
        pick_label = "Invite a friend"
        invite_label = "Get invite link"
        incoming_label = "Incoming invitations"
        if pending_count:
            incoming_label = f"Incoming invitations ({pending_count})"

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=pick_label, callback_data="friends:pick")],
            [InlineKeyboardButton(text=invite_label, callback_data="friends:invite")],
            [InlineKeyboardButton(text=incoming_label, callback_data="friends:incoming")],
        ]
    )


def invite_confirm_keyboard(friendship_id: UUID, lang: str) -> InlineKeyboardMarkup:
    accept_label = "Подтвердить" if lang == "ru" else "Accept"
    reject_label = "Отклонить" if lang == "ru" else "Decline"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=accept_label,
                    callback_data=f"friend:accept:{friendship_id}",
                ),
                InlineKeyboardButton(
                    text=reject_label,
                    callback_data=f"friend:reject:{friendship_id}",
                ),
            ],
        ]
    )


def friends_incoming_keyboard(
    friendship_ids: Sequence[UUID],
    lang: str,
) -> InlineKeyboardMarkup:
    accept_label = "Подтвердить" if lang == "ru" else "Accept"
    reject_label = "Отклонить" if lang == "ru" else "Decline"
    back_label = "Назад" if lang == "ru" else "Back"
    rows: list[list[InlineKeyboardButton]] = []
    for i, friendship_id in enumerate(friendship_ids, start=1):
        prefix = f"{i}. " if len(friendship_ids) > 1 else ""
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"{prefix}{accept_label}",
                    callback_data=f"friend:accept:{friendship_id}",
                ),
                InlineKeyboardButton(
                    text=reject_label,
                    callback_data=f"friend:reject:{friendship_id}",
                ),
            ]
        )
    rows.append([InlineKeyboardButton(text=back_label, callback_data="friends:main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def empty_feed_keyboard(lang: str) -> InlineKeyboardMarkup:
    if lang == "ru":
        add_label = "➕ Добавить событие"
        stats_label = "📊 Статистика"
    else:
        add_label = "➕ Add event"
        stats_label = "📊 Stats"

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=add_label, callback_data="nav:add"),
                InlineKeyboardButton(text=stats_label, callback_data="nav:stats"),
            ],
        ]
    )
