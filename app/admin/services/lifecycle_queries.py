from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

import asyncpg

from app.admin.pagination import PageResult, page_offset

PRESETS = {
    "": "Все",
    "no_shows": "Без показов (24h+)",
    "high_skip": "Высокий skip",
    "fast_rating": "Быстрый набор оценок",
    "slow_rating": "Медленный (показ, 0 оценок)",
    "disputed": "Спорные",
    "ai_pool": "AI в пуле",
}


@dataclass(frozen=True)
class LifecycleFilters:
    preset: str | None = None
    source: str | None = None
    category: str | None = None
    event_type: str | None = None
    created_from: date | None = None
    created_to: date | None = None
    is_deleted: str | None = None
    is_feed_hidden: str | None = None
    event_id: UUID | None = None


@dataclass(frozen=True)
class LifecycleRow:
    event_id: UUID
    preview: str
    source: str
    event_type: str
    category: str | None
    created_at: datetime
    first_shown_at: datetime | None
    first_rated_at: datetime | None
    impressions_count: int
    skips_count: int
    ratings_total: int
    ratings_community: int
    skip_rate: float | None
    hours_to_first_show: float | None
    hours_to_first_rating: float | None
    pool_wait_hours: float | None
    dispute_delta: float | None
    is_deleted: bool
    is_feed_hidden: bool


@dataclass(frozen=True)
class LifecycleKPIs:
    median_hours_to_first_rating: float | None
    median_skip_rate: float | None


class LifecycleQueries:
    PER_PAGE = 50

    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    def parse_filters(self, query: dict[str, str]) -> LifecycleFilters:
        preset = (query.get("preset") or "").strip() or None
        if preset and preset not in PRESETS:
            preset = None
        source = (query.get("source") or "").strip() or None
        if source not in (None, "seed", "user", "ai_generated"):
            source = None
        event_type = (query.get("event_type") or "").strip() or None
        if event_type not in (None, "real", "hypothetical"):
            event_type = None
        is_deleted = (query.get("is_deleted") or "").strip() or None
        if is_deleted not in (None, "yes", "no"):
            is_deleted = None
        is_feed_hidden = (query.get("is_feed_hidden") or "").strip() or None
        if is_feed_hidden not in (None, "yes", "no"):
            is_feed_hidden = None
        event_id = None
        raw_id = (query.get("event_id") or "").strip()
        if raw_id:
            try:
                event_id = UUID(raw_id)
            except ValueError:
                event_id = None
        return LifecycleFilters(
            preset=preset,
            source=source,
            category=(query.get("category") or "").strip() or None,
            event_type=event_type,
            created_from=self._parse_date(query.get("created_from")),
            created_to=self._parse_date(query.get("created_to")),
            is_deleted=is_deleted,
            is_feed_hidden=is_feed_hidden,
            event_id=event_id,
        )

    def filters_to_dict(self, filters: LifecycleFilters) -> dict[str, str | None]:
        return {
            "preset": filters.preset,
            "source": filters.source,
            "category": filters.category,
            "event_type": filters.event_type,
            "created_from": filters.created_from.isoformat() if filters.created_from else None,
            "created_to": filters.created_to.isoformat() if filters.created_to else None,
            "is_deleted": filters.is_deleted,
            "is_feed_hidden": filters.is_feed_hidden,
            "event_id": str(filters.event_id) if filters.event_id else None,
        }

    async def list_lifecycle(
        self, filters: LifecycleFilters, page: int
    ) -> PageResult:
        where, params, order_by = self._build_query(filters)
        param_idx = len(params) + 1

        total = await self._pool.fetchval(
            f"select count(*)::int from event_lifecycle_summary ls {where}",
            *params,
        )

        rows = await self._pool.fetch(
            f"""
            select
              event_id, preview, source::text, event_type::text, category,
              created_at, first_shown_at, first_rated_at,
              impressions_count, skips_count, ratings_total, ratings_community,
              skip_rate, hours_to_first_show, hours_to_first_rating,
              pool_wait_hours, dispute_delta, is_deleted, is_feed_hidden
            from event_lifecycle_summary ls
            {where}
            order by {order_by}
            limit ${param_idx} offset ${param_idx + 1}
            """,
            *params,
            self.PER_PAGE,
            page_offset(page, self.PER_PAGE),
        )

        items = [self._row_to_lifecycle(r) for r in rows]
        return PageResult(items=items, page=page, per_page=self.PER_PAGE, total=total)

    async def fetch_kpis(self) -> LifecycleKPIs:
        row = await self._pool.fetchrow(
            """
            select
              percentile_cont(0.5) within group (order by hours_to_first_rating)
                filter (where hours_to_first_rating is not null) as median_hours,
              percentile_cont(0.5) within group (order by skip_rate)
                filter (where skip_rate is not null and impressions_count >= 3)
                as median_skip
            from event_lifecycle_summary
            """
        )
        if not row:
            return LifecycleKPIs(
                median_hours_to_first_rating=None,
                median_skip_rate=None,
            )
        return LifecycleKPIs(
            median_hours_to_first_rating=self._to_float(row["median_hours"]),
            median_skip_rate=self._to_float(row["median_skip"]),
        )

    async def list_categories(self) -> list[str]:
        rows = await self._pool.fetch(
            """
            select distinct category from event_lifecycle_summary
            where category is not null and category <> ''
            order by category
            """
        )
        return [r["category"] for r in rows]

    def _build_query(self, filters: LifecycleFilters) -> tuple[str, list, str]:
        clauses: list[str] = []
        params: list = []
        order_by = "ls.created_at desc"

        if filters.event_id:
            params.append(filters.event_id)
            clauses.append(f"ls.event_id = ${len(params)}")

        preset = filters.preset
        if preset == "no_shows":
            clauses.append("ls.impressions_count = 0")
            clauses.append("ls.created_at < now() - interval '24 hours'")
        elif preset == "high_skip":
            clauses.append("ls.skip_rate >= 0.5")
            clauses.append("ls.impressions_count >= 3")
            order_by = "ls.skip_rate desc nulls last"
        elif preset == "fast_rating":
            clauses.append("ls.hours_to_first_rating is not null")
            order_by = "ls.hours_to_first_rating asc nulls last"
        elif preset == "slow_rating":
            clauses.append("ls.first_shown_at is not null")
            clauses.append("ls.ratings_total = 0")
            clauses.append("ls.created_at < now() - interval '48 hours'")
        elif preset == "disputed":
            clauses.append("ls.dispute_delta >= 3")
            clauses.append("ls.ratings_community >= 5")
            order_by = "ls.dispute_delta desc nulls last"
        elif preset == "ai_pool":
            clauses.append("ls.source = 'ai_generated'::event_source")
            clauses.append("ls.impressions_count = 0")
            clauses.append("ls.created_at < now() - interval '24 hours'")
            order_by = "ls.created_at asc"

        if filters.source:
            params.append(filters.source)
            clauses.append(f"ls.source = ${len(params)}::event_source")
        if filters.category:
            params.append(filters.category)
            clauses.append(f"ls.category = ${len(params)}")
        if filters.event_type:
            params.append(filters.event_type)
            clauses.append(f"ls.event_type = ${len(params)}::event_type")
        if filters.created_from:
            params.append(filters.created_from)
            clauses.append(f"ls.created_at::date >= ${len(params)}")
        if filters.created_to:
            params.append(filters.created_to)
            clauses.append(f"ls.created_at::date <= ${len(params)}")
        if filters.is_deleted == "yes":
            clauses.append("ls.is_deleted = true")
        elif filters.is_deleted == "no":
            clauses.append("ls.is_deleted = false")
        if filters.is_feed_hidden == "yes":
            clauses.append("ls.is_feed_hidden = true")
        elif filters.is_feed_hidden == "no":
            clauses.append("ls.is_feed_hidden = false")

        where = f"where {' and '.join(clauses)}" if clauses else ""
        return where, params, order_by

    @staticmethod
    def _row_to_lifecycle(row: asyncpg.Record) -> LifecycleRow:
        return LifecycleRow(
            event_id=row["event_id"],
            preview=row["preview"],
            source=row["source"],
            event_type=row["event_type"],
            category=row["category"],
            created_at=row["created_at"],
            first_shown_at=row["first_shown_at"],
            first_rated_at=row["first_rated_at"],
            impressions_count=row["impressions_count"],
            skips_count=row["skips_count"],
            ratings_total=row["ratings_total"],
            ratings_community=row["ratings_community"],
            skip_rate=LifecycleQueries._to_float(row["skip_rate"]),
            hours_to_first_show=LifecycleQueries._to_float(row["hours_to_first_show"]),
            hours_to_first_rating=LifecycleQueries._to_float(row["hours_to_first_rating"]),
            pool_wait_hours=LifecycleQueries._to_float(row["pool_wait_hours"]),
            dispute_delta=LifecycleQueries._to_float(row["dispute_delta"]),
            is_deleted=row["is_deleted"],
            is_feed_hidden=row["is_feed_hidden"],
        )

    @staticmethod
    def _to_float(value) -> float | None:
        if value is None:
            return None
        if isinstance(value, Decimal):
            return float(value)
        return float(value)

    @staticmethod
    def _parse_date(raw: str | None) -> date | None:
        if not raw:
            return None
        try:
            return date.fromisoformat(raw)
        except ValueError:
            return None
