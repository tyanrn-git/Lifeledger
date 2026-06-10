from decimal import Decimal

# Порог количества оценок → (вес AI, вес пользователей)
_WEIGHT_THRESHOLDS: list[tuple[int, float, float]] = [
    (0, 1.0, 0.0),
    (10, 0.9, 0.1),
    (50, 0.8, 0.2),
    (100, 0.5, 0.5),
    (500, 0.2, 0.8),
    (1000, 0.0, 1.0),
]


def get_ai_user_weights(ratings_count: int) -> tuple[float, float]:
    ai_weight, user_weight = 1.0, 0.0
    for threshold, ai, user in _WEIGHT_THRESHOLDS:
        if ratings_count >= threshold:
            ai_weight, user_weight = ai, user
    return ai_weight, user_weight


def calculate_final_community_score(
    ai_score: float | Decimal | None,
    community_user_score: float | Decimal | None,
    ratings_count: int,
) -> float | None:
    if ai_score is None:
        return float(community_user_score) if community_user_score is not None else None
    if ratings_count == 0 or community_user_score is None:
        return float(ai_score)
    ai_weight, user_weight = get_ai_user_weights(ratings_count)
    return float(ai_score) * ai_weight + float(community_user_score) * user_weight


def format_score(value: int | float | Decimal | None) -> str:
    if value is None:
        return "—"
    number = float(value)
    if number == int(number):
        signed = f"{int(number):+d}" if number != 0 else "0"
        return signed
    signed = f"{number:+.1f}"
    return signed
