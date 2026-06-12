from dataclasses import dataclass

import asyncpg


@dataclass(frozen=True)
class ScoreBucket:
    score: int
    count: int


@dataclass(frozen=True)
class BreakdownRow:
    key: str
    count: int
    avg_score: float | None


@dataclass(frozen=True)
class DeviationRow:
    event_id: str
    preview: str
    self_score: int
    final_community_score: float
    delta: float


@dataclass(frozen=True)
class RatingsSummary:
    histogram: list[ScoreBucket]
    avg_self: float | None
    avg_friends: float | None
    avg_community: float | None
    avg_ai: float | None
    avg_rating_score: float | None
    by_category: list[BreakdownRow]
    by_language: list[BreakdownRow]
    self_vs_community: list[DeviationRow]
    histogram_json: str


class RatingsQueries:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def fetch_summary(self) -> RatingsSummary:
        hist_rows = await self._pool.fetch(
            """
            select score, count(*)::int as cnt
            from ratings
            group by score
            order by score
            """
        )
        histogram = [ScoreBucket(score=r["score"], count=r["cnt"]) for r in hist_rows]

        avgs = await self._pool.fetchrow(
            """
            select
              avg(self_score)::numeric(5,2) as avg_self,
              avg(friends_score)::numeric(5,2) as avg_friends,
              avg(final_community_score)::numeric(5,2) as avg_community,
              avg(ai_score)::numeric(5,2) as avg_ai
            from events
            where is_deleted = false
            """
        )
        avg_rating = await self._pool.fetchval(
            "select avg(score)::numeric(5,2) from ratings"
        )

        cat_rows = await self._pool.fetch(
            """
            select e.category as key, count(*)::int as cnt,
                   avg(r.score)::numeric(5,2) as avg_score
            from ratings r
            join events e on e.id = r.event_id
            where e.is_deleted = false and e.category is not null
            group by e.category
            order by cnt desc
            limit 20
            """
        )
        lang_rows = await self._pool.fetch(
            """
            select e.original_language as key, count(*)::int as cnt,
                   avg(r.score)::numeric(5,2) as avg_score
            from ratings r
            join events e on e.id = r.event_id
            where e.is_deleted = false
            group by e.original_language
            order by cnt desc
            limit 20
            """
        )
        dev_rows = await self._pool.fetch(
            """
            select id, left(coalesce(normalized_text, original_text), 60) as preview,
                   self_score, final_community_score,
                   abs(self_score - final_community_score)::numeric(5,2) as delta
            from events
            where is_deleted = false and final_community_score is not null
            order by delta desc
            limit 20
            """
        )

        import json

        hist_map = {b.score: b.count for b in histogram}
        chart_points = [{"score": s, "count": hist_map.get(s, 0)} for s in range(-10, 11)]

        return RatingsSummary(
            histogram=histogram,
            avg_self=_f(avgs["avg_self"]),
            avg_friends=_f(avgs["avg_friends"]),
            avg_community=_f(avgs["avg_community"]),
            avg_ai=_f(avgs["avg_ai"]),
            avg_rating_score=_f(avg_rating),
            by_category=[
                BreakdownRow(key=r["key"], count=r["cnt"], avg_score=_f(r["avg_score"]))
                for r in cat_rows
            ],
            by_language=[
                BreakdownRow(key=r["key"], count=r["cnt"], avg_score=_f(r["avg_score"]))
                for r in lang_rows
            ],
            self_vs_community=[
                DeviationRow(
                    event_id=str(r["id"]),
                    preview=r["preview"],
                    self_score=r["self_score"],
                    final_community_score=float(r["final_community_score"]),
                    delta=float(r["delta"]),
                )
                for r in dev_rows
            ],
            histogram_json=json.dumps(chart_points),
        )


def _f(val) -> float | None:
    if val is None:
        return None
    return float(val)
