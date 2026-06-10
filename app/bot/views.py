from uuid import UUID

from app.i18n import t
from app.schemas.events import Event, EventForRating
from app.schemas.stats import AuthorStats, EvaluatorStats, RatingLine
from app.utils.scoring import format_score


def event_type_label(event_type: str, lang: str) -> str:
    key = "event_type_real" if event_type == "real" else "event_type_hypothetical"
    return t(key, lang)


def event_scores_block(event: Event, lang: str) -> str:
    friends = format_score(event.friends_score)
    community = format_score(event.final_community_score)
    if lang == "ru":
        return (
            f"Моя оценка: {format_score(event.self_score)}\n"
            f"Друзья: {friends}\n"
            f"Сообщество: {community}"
        )
    return (
        f"My score: {format_score(event.self_score)}\n"
        f"Friends: {friends}\n"
        f"Community: {community}"
    )


def event_detail_text(event: Event, lang: str) -> str:
    return f"{event_type_label(event.event_type, lang)}\n\n{event.normalized_text}\n\n{event_scores_block(event, lang)}"


def event_list_item_text(index: int, event: Event, lang: str) -> str:
    return f"{index}. {event.normalized_text}\n{event_scores_block(event, lang)}"


def event_added_text(event: Event, lang: str) -> str:
    header = "Событие добавлено." if lang == "ru" else "Event added."
    return f"{header}\n\n{event_scores_block(event, lang)}"


def event_card_text(event: EventForRating, lang: str, display_text: str | None = None) -> str:
    type_key = "event_type_real" if event.event_type == "real" else "event_type_hypothetical"
    text = display_text if display_text is not None else event.normalized_text
    return f"{t(type_key, lang)}\n\n{text}\n\n{t('rate_prompt', lang)}"


def rating_result_text(score: int, event: EventForRating, lang: str) -> str:
    community = format_score(event.final_community_score)
    return (
        f"{t('your_score', lang, score=format_score(score))}\n\n"
        f"{t('community_score', lang, score=community)}"
    )


def _fmt_stat(value: float | None) -> str:
    return format_score(value) if value is not None else "—"


def _dynamics_line(label: str, line: RatingLine, lang: str) -> str:
    d7 = _fmt_stat(line.dynamics_7d)
    d30 = _fmt_stat(line.dynamics_30d)
    d90 = _fmt_stat(line.dynamics_90d)
    if lang == "ru":
        return f"{label}: 7 дн. {d7}  |  30 дн. {d30}  |  90 дн. {d90}"
    return f"{label}: 7d {d7}  |  30d {d30}  |  90d {d90}"


def stats_text(author: AuthorStats, evaluator: EvaluatorStats, lang: str) -> str:
    if lang == "ru":
        self_l = "Самооценка"
        friends_l = "Друзья"
        community_l = "Сообщество"
        lines = [
            t("stats_author_title", lang),
            "",
            t("stats_rating_title", lang),
            f"{self_l}: {_fmt_stat(author.self_line.total)}",
            f"{friends_l}: {_fmt_stat(author.friends_line.total)}",
            f"{community_l}: {_fmt_stat(author.community_line.total)}",
            "",
            t("stats_average_title", lang),
            f"{self_l}: {_fmt_stat(author.self_line.average)}",
            f"{friends_l}: {_fmt_stat(author.friends_line.average)}",
            f"{community_l}: {_fmt_stat(author.community_line.average)}",
            "",
            t("stats_dynamics_title", lang),
            _dynamics_line(self_l, author.self_line, lang),
            _dynamics_line(friends_l, author.friends_line, lang),
            _dynamics_line(community_l, author.community_line, lang),
            "",
            t("stats_evaluator_title", lang),
            "",
            t("stats_rated_count", lang, count=evaluator.rated_events_count),
            t("stats_you_rated", lang, score=_fmt_stat(evaluator.user_average)),
            t("stats_community_rated", lang, score=_fmt_stat(evaluator.community_average)),
            t("stats_deviation", lang, score=_fmt_stat(evaluator.deviation)),
        ]
    else:
        self_l = "Self"
        friends_l = "Friends"
        community_l = "Community"
        lines = [
            t("stats_author_title", lang),
            "",
            t("stats_rating_title", lang),
            f"{self_l}: {_fmt_stat(author.self_line.total)}",
            f"{friends_l}: {_fmt_stat(author.friends_line.total)}",
            f"{community_l}: {_fmt_stat(author.community_line.total)}",
            "",
            t("stats_average_title", lang),
            f"{self_l}: {_fmt_stat(author.self_line.average)}",
            f"{friends_l}: {_fmt_stat(author.friends_line.average)}",
            f"{community_l}: {_fmt_stat(author.community_line.average)}",
            "",
            t("stats_dynamics_title", lang),
            _dynamics_line(self_l, author.self_line, lang),
            _dynamics_line(friends_l, author.friends_line, lang),
            _dynamics_line(community_l, author.community_line, lang),
            "",
            t("stats_evaluator_title", lang),
            "",
            t("stats_rated_count", lang, count=evaluator.rated_events_count),
            t("stats_you_rated", lang, score=_fmt_stat(evaluator.user_average)),
            t("stats_community_rated", lang, score=_fmt_stat(evaluator.community_average)),
            t("stats_deviation", lang, score=_fmt_stat(evaluator.deviation)),
        ]
    return "\n".join(lines)


def parse_uuid(value: str) -> UUID | None:
    try:
        return UUID(value)
    except ValueError:
        return None
