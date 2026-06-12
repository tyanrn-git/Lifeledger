import csv
import io
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

import asyncpg

EXPORT_TYPES = {
    "users": "Users",
    "events": "Events",
    "ratings": "Ratings",
    "admin_event_log": "Admin event log",
    "ai_audit": "AI audit (disputed)",
    "event_lifecycle": "Event lifecycle",
}

MAX_ROWS = 50_000
MAX_DAYS = 90


@dataclass(frozen=True)
class ExportRequest:
    export_type: str
    date_from: date
    date_to: date


@dataclass(frozen=True)
class ExportResult:
    filename: str
    row_count: int
    csv_text: str


class ExportService:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    def parse_request(self, export_type: str, date_from: str, date_to: str) -> ExportRequest:
        if export_type not in EXPORT_TYPES:
            raise ValueError("unknown export type")
        start = self._parse_date(date_from)
        end = self._parse_date(date_to)
        if not start or not end:
            raise ValueError("date range required")
        if end < start:
            raise ValueError("date_to must be >= date_from")
        if (end - start).days > MAX_DAYS:
            raise ValueError(f"max range is {MAX_DAYS} days")
        return ExportRequest(export_type=export_type, date_from=start, date_to=end)

    async def generate(self, req: ExportRequest) -> ExportResult:
        end_exclusive = req.date_to + timedelta(days=1)
        count = await self._count_rows(req, end_exclusive)
        if count > MAX_ROWS:
            raise ValueError(f"too many rows ({count}), narrow the filter (max {MAX_ROWS})")

        rows, headers = await self._fetch_rows(req, end_exclusive)
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(headers)
        for row in rows:
            writer.writerow([self._cell(row[h]) for h in headers])

        filename = f"{req.export_type}_{req.date_from.isoformat()}_{req.date_to.isoformat()}.csv"
        return ExportResult(
            filename=filename,
            row_count=len(rows),
            csv_text=buffer.getvalue(),
        )

    async def _count_rows(self, req: ExportRequest, end_exclusive: date) -> int:
        query, params = self._count_query(req, end_exclusive)
        val = await self._pool.fetchval(query, *params)
        return int(val or 0)

    async def _fetch_rows(
        self, req: ExportRequest, end_exclusive: date
    ) -> tuple[list[asyncpg.Record], list[str]]:
        if req.export_type == "users":
            rows = await self._pool.fetch(
                """
                select id, telegram_id, username, first_name, last_name,
                       language_code, notifications_enabled, created_at, last_seen_at
                from users
                where created_at >= $1 and created_at < $2
                order by created_at
                limit $3
                """,
                req.date_from,
                end_exclusive,
                MAX_ROWS,
            )
            headers = [
                "id", "telegram_id", "username", "first_name", "last_name",
                "language_code", "notifications_enabled", "created_at", "last_seen_at",
            ]
        elif req.export_type == "events":
            rows = await self._pool.fetch(
                """
                select id, author_user_id, source::text, event_type::text, category,
                       original_language, self_score, ai_score, final_community_score,
                       community_ratings_count, is_deleted, is_feed_hidden, created_at
                from events
                where created_at >= $1 and created_at < $2
                order by created_at
                limit $3
                """,
                req.date_from,
                end_exclusive,
                MAX_ROWS,
            )
            headers = [
                "id", "author_user_id", "source", "event_type", "category",
                "original_language", "self_score", "ai_score", "final_community_score",
                "community_ratings_count", "is_deleted", "is_feed_hidden", "created_at",
            ]
        elif req.export_type == "ratings":
            rows = await self._pool.fetch(
                """
                select r.id, r.event_id, r.rater_user_id, r.rating_scope::text,
                       r.score, r.created_at
                from ratings r
                where r.created_at >= $1 and r.created_at < $2
                order by r.created_at
                limit $3
                """,
                req.date_from,
                end_exclusive,
                MAX_ROWS,
            )
            headers = [
                "id", "event_id", "rater_user_id", "rating_scope", "score", "created_at",
            ]
        elif req.export_type == "admin_event_log":
            rows = await self._pool.fetch(
                """
                select id, user_id, event_name, properties::text, created_at
                from admin_event_log
                where created_at >= $1 and created_at < $2
                order by created_at
                limit $3
                """,
                req.date_from,
                end_exclusive,
                MAX_ROWS,
            )
            headers = ["id", "user_id", "event_name", "properties", "created_at"]
        elif req.export_type == "ai_audit":
            rows = await self._pool.fetch(
                """
                select id, left(coalesce(normalized_text, original_text), 120) as preview,
                       ai_score, community_user_score, final_community_score,
                       community_ratings_count, scoring_calibration_version, created_at
                from events
                where is_deleted = false
                  and community_ratings_count >= 5
                  and ai_score is not null
                  and community_user_score is not null
                  and abs(ai_score - community_user_score) >= 3
                  and created_at >= $1 and created_at < $2
                order by created_at
                limit $3
                """,
                req.date_from,
                end_exclusive,
                MAX_ROWS,
            )
            headers = [
                "id", "preview", "ai_score", "community_user_score",
                "final_community_score", "community_ratings_count",
                "scoring_calibration_version", "created_at",
            ]
        else:  # event_lifecycle
            rows = await self._pool.fetch(
                """
                select event_id, preview, source::text, event_type::text, category,
                       created_at, first_shown_at, first_rated_at,
                       impressions_count, skips_count, ratings_total, skip_rate,
                       hours_to_first_rating, dispute_delta, is_feed_hidden
                from event_lifecycle_summary
                where created_at >= $1 and created_at < $2
                order by created_at
                limit $3
                """,
                req.date_from,
                end_exclusive,
                MAX_ROWS,
            )
            headers = [
                "event_id", "preview", "source", "event_type", "category",
                "created_at", "first_shown_at", "first_rated_at",
                "impressions_count", "skips_count", "ratings_total", "skip_rate",
                "hours_to_first_rating", "dispute_delta", "is_feed_hidden",
            ]
        return rows, headers

    def _count_query(self, req: ExportRequest, end_exclusive: date) -> tuple[str, list]:
        if req.export_type == "users":
            return (
                "select count(*)::int from users where created_at >= $1 and created_at < $2",
                [req.date_from, end_exclusive],
            )
        if req.export_type == "events":
            return (
                "select count(*)::int from events where created_at >= $1 and created_at < $2",
                [req.date_from, end_exclusive],
            )
        if req.export_type == "ratings":
            return (
                "select count(*)::int from ratings where created_at >= $1 and created_at < $2",
                [req.date_from, end_exclusive],
            )
        if req.export_type == "admin_event_log":
            return (
                "select count(*)::int from admin_event_log where created_at >= $1 and created_at < $2",
                [req.date_from, end_exclusive],
            )
        if req.export_type == "ai_audit":
            return (
                """
                select count(*)::int from events
                where is_deleted = false
                  and community_ratings_count >= 5
                  and ai_score is not null
                  and community_user_score is not null
                  and abs(ai_score - community_user_score) >= 3
                  and created_at >= $1 and created_at < $2
                """,
                [req.date_from, end_exclusive],
            )
        return (
            """
            select count(*)::int from event_lifecycle_summary
            where created_at >= $1 and created_at < $2
            """,
            [req.date_from, end_exclusive],
        )

    @staticmethod
    def _parse_date(raw: str) -> date | None:
        if not raw:
            return None
        try:
            return date.fromisoformat(raw)
        except ValueError:
            return None

    @staticmethod
    def _cell(value) -> str:
        if value is None:
            return ""
        if isinstance(value, datetime):
            return value.isoformat()
        return str(value)

    @staticmethod
    def default_date_range() -> tuple[str, str]:
        end = datetime.now(timezone.utc).date()
        start = end - timedelta(days=7)
        return start.isoformat(), end.isoformat()
