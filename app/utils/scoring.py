from dataclasses import dataclass
from decimal import Decimal

SCORING_CALIBRATION_VERSION = 2

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


@dataclass(frozen=True)
class CommunityScoreBreakdown:
    ai_score: float | None
    community_user_score: float | None
    community_ratings_count: int
    ai_weight: float
    user_weight: float
    final_community_score: float | None

    def is_ai_only(self) -> bool:
        return self.community_ratings_count == 0 or self.community_user_score is None


def build_community_score_breakdown(
    ai_score: float | Decimal | None,
    community_user_score: float | Decimal | None,
    community_ratings_count: int,
) -> CommunityScoreBreakdown:
    ai_f = float(ai_score) if ai_score is not None else None
    community_f = (
        float(community_user_score) if community_user_score is not None else None
    )
    ai_weight, user_weight = get_ai_user_weights(community_ratings_count)

    if ai_f is None:
        final = community_f
    elif community_ratings_count == 0 or community_f is None:
        final = ai_f
        ai_weight, user_weight = 1.0, 0.0
    else:
        final = ai_f * ai_weight + community_f * user_weight

    return CommunityScoreBreakdown(
        ai_score=ai_f,
        community_user_score=community_f,
        community_ratings_count=community_ratings_count,
        ai_weight=ai_weight,
        user_weight=user_weight,
        final_community_score=final,
    )


def calculate_final_community_score(
    ai_score: float | Decimal | None,
    community_user_score: float | Decimal | None,
    ratings_count: int,
) -> float | None:
    return build_community_score_breakdown(
        ai_score, community_user_score, ratings_count
    ).final_community_score


def format_score(value: int | float | Decimal | None) -> str:
    if value is None:
        return "—"
    number = float(value)
    if number == int(number):
        signed = f"{int(number):+d}" if number != 0 else "0"
        return signed
    signed = f"{number:+.1f}"
    return signed
