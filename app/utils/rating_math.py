import math
from datetime import datetime, timedelta, timezone
from decimal import Decimal


def signed_quadratic_sum(scores: list[float]) -> float:
    total = 0.0
    for raw in scores:
        s = float(raw)
        sq = s * s
        if s > 0:
            total += sq
        elif s < 0:
            total -= sq
    return total


def rating_from_scores(scores: list[float]) -> float | None:
    if not scores:
        return None
    total = signed_quadratic_sum(scores)
    if total == 0:
        return 0.0
    sign = 1.0 if total > 0 else -1.0
    return sign * math.sqrt(abs(total))


def average_from_scores(scores: list[float]) -> float | None:
    if not scores:
        return None
    return sum(float(s) for s in scores) / len(scores)


def rating_delta(current_scores: list[float], past_scores: list[float]) -> float | None:
    current = rating_from_scores(current_scores)
    if current is None:
        return None
    past = rating_from_scores(past_scores) if past_scores else 0.0
    return current - past


def event_effective_date(event_time: datetime | None, created_at: datetime) -> datetime:
    return event_time if event_time is not None else created_at


def cutoff_utc(days: int) -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=days)


def to_float(value: int | float | Decimal | None) -> float | None:
    if value is None:
        return None
    return float(value)
