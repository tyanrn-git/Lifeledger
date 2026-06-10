from dataclasses import dataclass


@dataclass
class RatingLine:
    total: float | None
    average: float | None
    dynamics_7d: float | None
    dynamics_30d: float | None
    dynamics_90d: float | None


@dataclass
class AuthorStats:
    self_line: RatingLine
    friends_line: RatingLine
    community_line: RatingLine


@dataclass
class EvaluatorStats:
    rated_events_count: int
    user_average: float | None
    community_average: float | None
    deviation: float | None
