from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

import asyncpg

from app.admin.pagination import PageResult, page_offset


@dataclass(frozen=True)
class EventListRow:
    id: UUID
    preview: str
    source: str
    event_type: str
    category: str | None
    original_language: str
    author_user_id: UUID | None
    author_name: str | None
    self_score: int
    final_community_score: float | None
    community_ratings_count: int
    impressions_count: int
    is_deleted: bool
    is_feed_hidden: bool
    created_at: datetime


@dataclass(frozen=True)
class EventFilters:
    source: str | None = None
    category: str | None = None
    language: str | None = None
    event_type: str | None = None
    score_min: float | None = None
    score_max: float | None = None
    is_deleted: str | None = None
    is_feed_hidden: str | None = None
    only: str | None = None


@dataclass(frozen=True)
class RatingRow:
    rater_user_id: UUID
    rating_scope: str
    score: int
    created_at: datetime


@dataclass(frozen=True)
class ImpressionRow:
    user_id: UUID
    status: str
    feed_tier: int | None
    batch_id: UUID | None
    shown_at: datetime
    rated_at: datetime | None
    skipped_at: datetime | None


@dataclass(frozen=True)
class TranslationRow:
    language_code: str
    translated_text: str
    updated_at: datetime


@dataclass(frozen=True)
class InjectionRow:
    created_at: datetime
    user_id: UUID | None
    properties: str


@dataclass(frozen=True)
class EventDetail:
    id: UUID
    author_user_id: UUID | None
    author_name: str | None
    event_type: str
    source: str
    original_text: str
    normalized_text: str
    original_language: str
    action_text: str | None
    context_text: str | None
    category: str | None
    self_score: int
    ai_score: float | None
    community_user_score: float | None
    final_community_score: float | None
    friends_score: float | None
    community_ai_weight: float | None
    community_user_weight: float | None
    scoring_calibration_version: int
    community_ratings_count: int
    friends_ratings_count: int
    is_deleted: bool
    is_feed_hidden: bool
    created_at: datetime
    ratings: list[RatingRow]
    impressions: list[ImpressionRow]
    translations: list[TranslationRow]
    injections: list[InjectionRow]
    impressions_count: int
    skips_count: int


class EventsQueries:
    PER_PAGE = 50

    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    def parse_filters(self, query: dict[str, str]) -> EventFilters:
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
        only = (query.get("only") or "").strip() or None
        if only not in (None, "ai", "user"):
            only = None
        return EventFilters(
            source=source,
            category=(query.get("category") or "").strip() or None,
            language=(query.get("language") or "").strip() or None,
            event_type=event_type,
            score_min=self._parse_float(query.get("score_min")),
            score_max=self._parse_float(query.get("score_max")),
            is_deleted=is_deleted,
            is_feed_hidden=is_feed_hidden,
            only=only,
        )

    def filters_to_dict(self, filters: EventFilters) -> dict[str, str | None]:
        return {
            "source": filters.source,
            "category": filters.category,
            "language": filters.language,
            "event_type": filters.event_type,
            "score_min": str(filters.score_min) if filters.score_min is not None else None,
            "score_max": str(filters.score_max) if filters.score_max is not None else None,
            "is_deleted": filters.is_deleted,
            "is_feed_hidden": filters.is_feed_hidden,
            "only": filters.only,
        }

    async def list_events(
        self, filters: EventFilters, page: int
    ) -> PageResult:
        where, params = self._build_where(filters)
        param_idx = len(params) + 1

        total = await self._pool.fetchval(
            f"select count(*)::int from events e {where}",
            *params,
        )

        rows = await self._pool.fetch(
            f"""
            select
              e.id,
              left(coalesce(e.normalized_text, e.original_text), 80) as preview,
              e.source::text,
              e.event_type::text,
              e.category,
              e.original_language,
              e.author_user_id,
              coalesce(u.username, u.first_name) as author_name,
              e.self_score,
              e.final_community_score,
              e.community_ratings_count,
              e.is_deleted,
              e.is_feed_hidden,
              e.created_at,
              (select count(*)::int from event_impressions ei where ei.event_id = e.id)
                as impressions_count
            from events e
            left join users u on u.id = e.author_user_id
            {where}
            order by e.created_at desc
            limit ${param_idx} offset ${param_idx + 1}
            """,
            *params,
            self.PER_PAGE,
            page_offset(page, self.PER_PAGE),
        )

        items = [
            EventListRow(
                id=r["id"],
                preview=r["preview"],
                source=r["source"],
                event_type=r["event_type"],
                category=r["category"],
                original_language=r["original_language"],
                author_user_id=r["author_user_id"],
                author_name=r["author_name"],
                self_score=r["self_score"],
                final_community_score=float(r["final_community_score"])
                if r["final_community_score"] is not None
                else None,
                community_ratings_count=r["community_ratings_count"],
                impressions_count=r["impressions_count"],
                is_deleted=r["is_deleted"],
                is_feed_hidden=r["is_feed_hidden"],
                created_at=r["created_at"],
            )
            for r in rows
        ]
        return PageResult(items=items, page=page, per_page=self.PER_PAGE, total=total)

    async def get_event(self, event_id: UUID) -> EventDetail | None:
        row = await self._pool.fetchrow(
            """
            select e.*, coalesce(u.username, u.first_name) as author_name
            from events e
            left join users u on u.id = e.author_user_id
            where e.id = $1
            """,
            event_id,
        )
        if not row:
            return None

        rating_rows = await self._pool.fetch(
            """
            select rater_user_id, rating_scope::text, score, created_at
            from ratings
            where event_id = $1
            order by created_at
            """,
            event_id,
        )

        impression_rows = await self._pool.fetch(
            """
            select user_id, status::text, feed_tier, batch_id,
                   shown_at, rated_at, skipped_at
            from event_impressions
            where event_id = $1
            order by shown_at desc
            limit 100
            """,
            event_id,
        )

        translation_rows = await self._pool.fetch(
            """
            select language_code, translated_text, updated_at
            from event_translations
            where event_id = $1
            order by language_code
            """,
            event_id,
        )

        injection_rows = await self._pool.fetch(
            """
            select created_at, user_id, properties::text as properties
            from admin_event_log
            where event_name = 'event_injected_into_batch'
              and properties->>'event_id' = $1
            order by created_at desc
            limit 50
            """,
            str(event_id),
        )

        skips = sum(1 for i in impression_rows if i["status"] == "skipped")

        return EventDetail(
            id=row["id"],
            author_user_id=row["author_user_id"],
            author_name=row["author_name"],
            event_type=str(row["event_type"]),
            source=str(row["source"]),
            original_text=row["original_text"],
            normalized_text=row["normalized_text"] or row["original_text"],
            original_language=row["original_language"],
            action_text=row["action_text"],
            context_text=row["context_text"],
            category=row["category"],
            self_score=row["self_score"],
            ai_score=float(row["ai_score"]) if row["ai_score"] is not None else None,
            community_user_score=float(row["community_user_score"])
            if row["community_user_score"] is not None
            else None,
            final_community_score=float(row["final_community_score"])
            if row["final_community_score"] is not None
            else None,
            friends_score=float(row["friends_score"])
            if row["friends_score"] is not None
            else None,
            community_ai_weight=float(row["community_ai_weight"])
            if row["community_ai_weight"] is not None
            else None,
            community_user_weight=float(row["community_user_weight"])
            if row["community_user_weight"] is not None
            else None,
            scoring_calibration_version=row["scoring_calibration_version"],
            community_ratings_count=row["community_ratings_count"],
            friends_ratings_count=row["friends_ratings_count"],
            is_deleted=row["is_deleted"],
            is_feed_hidden=row["is_feed_hidden"],
            created_at=row["created_at"],
            ratings=[
                RatingRow(
                    rater_user_id=r["rater_user_id"],
                    rating_scope=r["rating_scope"],
                    score=r["score"],
                    created_at=r["created_at"],
                )
                for r in rating_rows
            ],
            impressions=[
                ImpressionRow(
                    user_id=i["user_id"],
                    status=i["status"],
                    feed_tier=i["feed_tier"],
                    batch_id=i["batch_id"],
                    shown_at=i["shown_at"],
                    rated_at=i["rated_at"],
                    skipped_at=i["skipped_at"],
                )
                for i in impression_rows
            ],
            translations=[
                TranslationRow(
                    language_code=t["language_code"],
                    translated_text=t["translated_text"],
                    updated_at=t["updated_at"],
                )
                for t in translation_rows
            ],
            injections=[
                InjectionRow(
                    created_at=j["created_at"],
                    user_id=j["user_id"],
                    properties=j["properties"][:200],
                )
                for j in injection_rows
            ],
            impressions_count=len(impression_rows),
            skips_count=skips,
        )

    async def list_categories(self) -> list[str]:
        rows = await self._pool.fetch(
            """
            select distinct category from events
            where category is not null and category <> ''
            order by category
            """
        )
        return [r["category"] for r in rows]

    def _build_where(self, filters: EventFilters) -> tuple[str, list]:
        clauses: list[str] = []
        params: list = []

        if filters.only == "ai":
            params.append("ai_generated")
            clauses.append(f"e.source = ${len(params)}::event_source")
        elif filters.only == "user":
            params.append("user")
            clauses.append(f"e.source = ${len(params)}::event_source")
        elif filters.source:
            params.append(filters.source)
            clauses.append(f"e.source = ${len(params)}::event_source")

        if filters.category:
            params.append(filters.category)
            clauses.append(f"e.category = ${len(params)}")
        if filters.language:
            params.append(filters.language)
            clauses.append(f"e.original_language = ${len(params)}")
        if filters.event_type:
            params.append(filters.event_type)
            clauses.append(f"e.event_type = ${len(params)}::event_type")
        if filters.score_min is not None:
            params.append(filters.score_min)
            clauses.append(f"e.final_community_score >= ${len(params)}")
        if filters.score_max is not None:
            params.append(filters.score_max)
            clauses.append(f"e.final_community_score <= ${len(params)}")
        if filters.is_deleted == "yes":
            clauses.append("e.is_deleted = true")
        elif filters.is_deleted == "no":
            clauses.append("e.is_deleted = false")
        if filters.is_feed_hidden == "yes":
            clauses.append("e.is_feed_hidden = true")
        elif filters.is_feed_hidden == "no":
            clauses.append("e.is_feed_hidden = false")

        where = f"where {' and '.join(clauses)}" if clauses else ""
        return where, params

    @staticmethod
    def _parse_float(raw: str | None) -> float | None:
        if not raw:
            return None
        try:
            return float(raw)
        except ValueError:
            return None
