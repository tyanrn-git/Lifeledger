from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID

import asyncpg

from app.admin.pagination import PageResult, page_offset
from app.db.repositories.stats import StatsRepository


@dataclass(frozen=True)
class UserListRow:
    id: UUID
    telegram_id: int
    username: str | None
    first_name: str | None
    last_name: str | None
    language_code: str
    created_at: datetime
    last_seen_at: datetime | None
    events_count: int
    ratings_count: int
    friends_count: int


@dataclass(frozen=True)
class UserFilters:
    reg_from: date | None = None
    reg_to: date | None = None
    language: str | None = None
    has_events: str | None = None
    has_ratings: str | None = None
    active_days: int | None = None


@dataclass(frozen=True)
class FriendRow:
    id: UUID
    username: str | None
    first_name: str | None
    last_name: str | None


@dataclass(frozen=True)
class UserEventRow:
    id: UUID
    normalized_text: str
    event_type: str
    source: str
    created_at: datetime
    final_community_score: float | None


@dataclass(frozen=True)
class BatchRow:
    id: UUID
    created_at: datetime
    completed_at: datetime | None
    requested_size: int
    actual_size: int


@dataclass(frozen=True)
class TimelineRow:
    created_at: datetime
    event_name: str
    properties: str


@dataclass(frozen=True)
class UserDetail:
    id: UUID
    telegram_id: int
    username: str | None
    first_name: str | None
    last_name: str | None
    language_code: str
    notifications_enabled: bool
    created_at: datetime
    updated_at: datetime
    last_seen_at: datetime | None
    friends: list[FriendRow]
    events: list[UserEventRow]
    author_events_count: int
    rated_events_count: int
    user_average: float | None
    community_average: float | None
    timeline: list[TimelineRow]
    batches: list[BatchRow]


class UsersQueries:
    PER_PAGE = 50

    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool
        self._stats = StatsRepository(pool)

    def parse_filters(self, query: dict[str, str]) -> UserFilters:
        reg_from = self._parse_date(query.get("reg_from"))
        reg_to = self._parse_date(query.get("reg_to"))
        language = (query.get("language") or "").strip() or None
        has_events = (query.get("has_events") or "").strip() or None
        has_ratings = (query.get("has_ratings") or "").strip() or None
        active_days = self._parse_int(query.get("active_days"))
        return UserFilters(
            reg_from=reg_from,
            reg_to=reg_to,
            language=language,
            has_events=has_events if has_events in ("yes", "no") else None,
            has_ratings=has_ratings if has_ratings in ("yes", "no") else None,
            active_days=active_days,
        )

    def filters_to_dict(self, filters: UserFilters) -> dict[str, str | None]:
        return {
            "reg_from": filters.reg_from.isoformat() if filters.reg_from else None,
            "reg_to": filters.reg_to.isoformat() if filters.reg_to else None,
            "language": filters.language,
            "has_events": filters.has_events,
            "has_ratings": filters.has_ratings,
            "active_days": str(filters.active_days) if filters.active_days else None,
        }

    async def list_users(
        self, filters: UserFilters, page: int
    ) -> PageResult:
        where, params = self._build_where(filters)
        param_idx = len(params) + 1

        total = await self._pool.fetchval(
            f"select count(*)::int from users u {where}",
            *params,
        )

        rows = await self._pool.fetch(
            f"""
            select
              u.id, u.telegram_id, u.username, u.first_name, u.last_name,
              u.language_code, u.created_at, u.last_seen_at,
              (select count(*)::int from events e
               where e.author_user_id = u.id and e.is_deleted = false) as events_count,
              (select count(*)::int from ratings r
               where r.rater_user_id = u.id) as ratings_count,
              (select count(*)::int from friendships f
               where f.status = 'accepted'
                 and (f.requester_user_id = u.id or f.addressee_user_id = u.id)
              ) as friends_count
            from users u
            {where}
            order by u.created_at desc
            limit ${param_idx} offset ${param_idx + 1}
            """,
            *params,
            self.PER_PAGE,
            page_offset(page, self.PER_PAGE),
        )

        items = [
            UserListRow(
                id=r["id"],
                telegram_id=r["telegram_id"],
                username=r["username"],
                first_name=r["first_name"],
                last_name=r["last_name"],
                language_code=r["language_code"],
                created_at=r["created_at"],
                last_seen_at=r["last_seen_at"],
                events_count=r["events_count"],
                ratings_count=r["ratings_count"],
                friends_count=r["friends_count"],
            )
            for r in rows
        ]
        return PageResult(items=items, page=page, per_page=self.PER_PAGE, total=total)

    async def get_user(self, user_id: UUID) -> UserDetail | None:
        row = await self._pool.fetchrow(
            "select * from users where id = $1",
            user_id,
        )
        if not row:
            return None

        friend_rows = await self._pool.fetch(
            """
            select u.id, u.username, u.first_name, u.last_name
            from friendships f
            join users u on u.id = case
              when f.requester_user_id = $1 then f.addressee_user_id
              else f.requester_user_id
            end
            where f.status = 'accepted'
              and ($1 = f.requester_user_id or $1 = f.addressee_user_id)
            order by u.first_name nulls last, u.username nulls last
            """,
            user_id,
        )

        event_rows = await self._pool.fetch(
            """
            select id, coalesce(normalized_text, original_text) as normalized_text,
                   event_type::text, source::text, created_at, final_community_score
            from events
            where author_user_id = $1 and is_deleted = false
            order by created_at desc
            limit 50
            """,
            user_id,
        )

        author_events = await self._stats.list_author_real_events(user_id)
        evaluator = await self._stats.get_evaluator_aggregates(user_id)

        timeline_rows = await self._pool.fetch(
            """
            select created_at, event_name, properties::text as properties
            from admin_event_log
            where user_id = $1
            order by created_at desc
            limit 100
            """,
            user_id,
        )

        batch_rows = await self._pool.fetch(
            """
            select id, created_at, completed_at, requested_size, actual_size
            from rating_batches
            where user_id = $1
            order by created_at desc
            limit 20
            """,
            user_id,
        )

        return UserDetail(
            id=row["id"],
            telegram_id=row["telegram_id"],
            username=row["username"],
            first_name=row["first_name"],
            last_name=row["last_name"],
            language_code=row["language_code"],
            notifications_enabled=row["notifications_enabled"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            last_seen_at=row["last_seen_at"],
            friends=[
                FriendRow(
                    id=f["id"],
                    username=f["username"],
                    first_name=f["first_name"],
                    last_name=f["last_name"],
                )
                for f in friend_rows
            ],
            events=[
                UserEventRow(
                    id=e["id"],
                    normalized_text=e["normalized_text"][:120],
                    event_type=e["event_type"],
                    source=e["source"],
                    created_at=e["created_at"],
                    final_community_score=float(e["final_community_score"])
                    if e["final_community_score"] is not None
                    else None,
                )
                for e in event_rows
            ],
            author_events_count=len(author_events),
            rated_events_count=evaluator.rated_events_count,
            user_average=float(evaluator.user_average)
            if evaluator.user_average is not None
            else None,
            community_average=float(evaluator.community_average)
            if evaluator.community_average is not None
            else None,
            timeline=[
                TimelineRow(
                    created_at=t["created_at"],
                    event_name=t["event_name"],
                    properties=t["properties"][:200],
                )
                for t in timeline_rows
            ],
            batches=[
                BatchRow(
                    id=b["id"],
                    created_at=b["created_at"],
                    completed_at=b["completed_at"],
                    requested_size=b["requested_size"],
                    actual_size=b["actual_size"],
                )
                for b in batch_rows
            ],
        )

    def _build_where(self, filters: UserFilters) -> tuple[str, list]:
        clauses: list[str] = []
        params: list = []

        if filters.reg_from:
            params.append(filters.reg_from)
            clauses.append(f"u.created_at::date >= ${len(params)}")
        if filters.reg_to:
            params.append(filters.reg_to)
            clauses.append(f"u.created_at::date <= ${len(params)}")
        if filters.language:
            params.append(filters.language)
            clauses.append(f"u.language_code = ${len(params)}")
        if filters.active_days:
            params.append(filters.active_days)
            clauses.append(
                f"u.last_seen_at >= now() - ${len(params)} * interval '1 day'"
            )
        if filters.has_events == "yes":
            clauses.append(
                "exists (select 1 from events e where e.author_user_id = u.id and e.is_deleted = false)"
            )
        elif filters.has_events == "no":
            clauses.append(
                "not exists (select 1 from events e where e.author_user_id = u.id and e.is_deleted = false)"
            )
        if filters.has_ratings == "yes":
            clauses.append(
                "exists (select 1 from ratings r where r.rater_user_id = u.id)"
            )
        elif filters.has_ratings == "no":
            clauses.append(
                "not exists (select 1 from ratings r where r.rater_user_id = u.id)"
            )

        where = f"where {' and '.join(clauses)}" if clauses else ""
        return where, params

    @staticmethod
    def _parse_date(raw: str | None) -> date | None:
        if not raw:
            return None
        try:
            return date.fromisoformat(raw)
        except ValueError:
            return None

    @staticmethod
    def _parse_int(raw: str | None) -> int | None:
        if not raw:
            return None
        try:
            value = int(raw)
        except ValueError:
            return None
        return value if value > 0 else None

    @staticmethod
    def display_name(
        username: str | None,
        first_name: str | None,
        last_name: str | None,
    ) -> str:
        parts = [p for p in (first_name, last_name) if p]
        if parts:
            return " ".join(parts)
        if username:
            return f"@{username}"
        return "—"
