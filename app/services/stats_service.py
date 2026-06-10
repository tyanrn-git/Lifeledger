from collections.abc import Callable
from datetime import datetime
from uuid import UUID

from app.db.repositories.stats import AuthorEventRow, StatsRepository
from app.schemas.stats import AuthorStats, EvaluatorStats, RatingLine
from app.utils.rating_math import (
    average_from_scores,
    cutoff_utc,
    rating_delta,
    rating_from_scores,
    to_float,
)


class StatsService:
    def __init__(self, stats_repo: StatsRepository) -> None:
        self._stats = stats_repo

    async def calculate_author_stats(self, user_id: UUID) -> AuthorStats:
        events = await self._stats.list_author_real_events(user_id)
        return AuthorStats(
            self_line=self._build_line(events, lambda e: float(e.self_score)),
            friends_line=self._build_line(
                events,
                lambda e: to_float(e.friends_score),
                require_value=True,
            ),
            community_line=self._build_line(
                events,
                lambda e: to_float(e.final_community_score),
            ),
        )

    async def calculate_evaluator_stats(self, user_id: UUID) -> EvaluatorStats:
        row = await self._stats.get_evaluator_aggregates(user_id)
        if row.rated_events_count == 0:
            return EvaluatorStats(
                rated_events_count=0,
                user_average=None,
                community_average=None,
                deviation=None,
            )

        user_avg = to_float(row.user_average)
        community_avg = to_float(row.community_average)
        deviation = None
        if user_avg is not None and community_avg is not None:
            deviation = user_avg - community_avg

        return EvaluatorStats(
            rated_events_count=row.rated_events_count,
            user_average=user_avg,
            community_average=community_avg,
            deviation=deviation,
        )

    def _build_line(
        self,
        events: list[AuthorEventRow],
        score_fn: Callable[[AuthorEventRow], float | None],
        *,
        require_value: bool = False,
    ) -> RatingLine:
        scored = [(e, score_fn(e)) for e in events]
        if require_value:
            scored = [(e, s) for e, s in scored if s is not None]

        all_scores = [s for _, s in scored if s is not None]
        if require_value and not all_scores:
            return RatingLine(None, None, None, None, None)

        return RatingLine(
            total=rating_from_scores(all_scores),
            average=average_from_scores(all_scores),
            dynamics_7d=self._dynamics(scored, 7),
            dynamics_30d=self._dynamics(scored, 30),
            dynamics_90d=self._dynamics(scored, 90),
        )

    def _dynamics(
        self,
        scored: list[tuple[AuthorEventRow, float | None]],
        days: int,
    ) -> float | None:
        valid = [(e, s) for e, s in scored if s is not None]
        if not valid:
            return None

        cutoff = cutoff_utc(days)
        all_scores = [s for _, s in valid]
        past_scores = [s for e, s in valid if e.event_date <= cutoff]
        return rating_delta(all_scores, past_scores)
