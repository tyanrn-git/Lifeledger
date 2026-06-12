from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from uuid import UUID

import asyncpg

from app.admin.pagination import PageResult, page_offset
from app.analytics.event_catalog import (
    EVENT_CATALOG,
    EVENT_GROUPS,
    EVENT_LABELS,
    GROUP_EVENT_NAMES,
    NOISY_EVENT_NAMES,
)

MAX_DAYS = 90


@dataclass(frozen=True)
class ActivityFilters:
    date_from: date
    date_to: date
    user_id: UUID | None = None
    username: str | None = None
    event_name: str | None = None
    event_group: str | None = None
    event_id: UUID | None = None
    include_noisy: bool = False


@dataclass(frozen=True)
class ActivityRow:
    id: UUID
    created_at: datetime
    event_name: str
    event_label: str
    user_id: UUID | None
    user_display: str | None
    properties: str
    linked_event_id: UUID | None


class ActivityQueries:
    PER_PAGE = 50

    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    @staticmethod
    def default_date_range() -> tuple[str, str]:
        end = datetime.now(timezone.utc).date()
        start = end - timedelta(days=90)
        return start.isoformat(), end.isoformat()

    def parse_filters(self, query: dict[str, str]) -> ActivityFilters:
        date_from = self._parse_date(query.get("date_from"))
        date_to = self._parse_date(query.get("date_to"))
        if not date_from or not date_to:
            date_from, date_to = map(date.fromisoformat, self.default_date_range())
        if date_to < date_from:
            date_to = date_from
        if (date_to - date_from).days > MAX_DAYS:
            date_from = date_to - timedelta(days=MAX_DAYS)

        user_id = None
        raw_user = (query.get("user_id") or "").strip()
        if raw_user:
            try:
                user_id = UUID(raw_user)
            except ValueError:
                user_id = None

        event_name = (query.get("event_name") or "").strip() or None
        if event_name and event_name not in EVENT_LABELS:
            event_name = None

        event_group = (query.get("event_group") or "").strip() or None
        if event_group and event_group not in EVENT_GROUPS:
            event_group = None

        event_id = None
        raw_event = (query.get("event_id") or "").strip()
        if raw_event:
            try:
                event_id = UUID(raw_event)
            except ValueError:
                event_id = None

        include_noisy = (query.get("include_noisy") or "").strip() == "yes"

        return ActivityFilters(
            date_from=date_from,
            date_to=date_to,
            user_id=user_id,
            username=(query.get("username") or "").strip() or None,
            event_name=event_name,
            event_group=event_group,
            event_id=event_id,
            include_noisy=include_noisy,
        )

    def filters_to_dict(self, filters: ActivityFilters) -> dict[str, str | None]:
        return {
            "date_from": filters.date_from.isoformat(),
            "date_to": filters.date_to.isoformat(),
            "user_id": str(filters.user_id) if filters.user_id else None,
            "username": filters.username,
            "event_name": filters.event_name,
            "event_group": filters.event_group,
            "event_id": str(filters.event_id) if filters.event_id else None,
            "include_noisy": "yes" if filters.include_noisy else None,
        }

    async def list_activity(
        self, filters: ActivityFilters, page: int
    ) -> PageResult:
        where, params = self._build_where(filters)
        end_exclusive = filters.date_to + timedelta(days=1)
        date_from_idx = len(params) + 1
        date_to_idx = len(params) + 2
        params.extend([filters.date_from, end_exclusive])

        count_sql = f"""
            select count(*)::int
            from admin_event_log l
            left join users u on u.id = l.user_id
            where {where}
              and l.created_at >= ${date_from_idx} and l.created_at < ${date_to_idx}
        """
        total = await self._pool.fetchval(count_sql, *params) or 0

        offset = page_offset(page, self.PER_PAGE)
        limit_idx = len(params) + 1
        offset_idx = len(params) + 2
        list_params = [*params, self.PER_PAGE, offset]

        rows = await self._pool.fetch(
            f"""
            select l.id, l.created_at, l.event_name, l.user_id,
                   l.properties::text as properties,
                   u.username, u.first_name, u.last_name, u.telegram_id,
                   nullif(l.properties->>'event_id', '') as linked_event_id_raw
            from admin_event_log l
            left join users u on u.id = l.user_id
            where {where}
              and l.created_at >= ${date_from_idx} and l.created_at < ${date_to_idx}
            order by l.created_at desc
            limit ${limit_idx} offset ${offset_idx}
            """,
            *list_params,
        )

        items = [self._row_to_activity(r) for r in rows]
        return PageResult(items=items, page=page, per_page=self.PER_PAGE, total=total)

    async def count_hidden_noisy(self, filters: ActivityFilters) -> int:
        if filters.include_noisy or filters.event_name:
            return 0
        if filters.event_group and not (
            set(GROUP_EVENT_NAMES.get(filters.event_group, [])) & NOISY_EVENT_NAMES
        ):
            return 0

        where, params = self._build_where(
            ActivityFilters(
                date_from=filters.date_from,
                date_to=filters.date_to,
                user_id=filters.user_id,
                username=filters.username,
                event_name=None,
                event_group=filters.event_group,
                event_id=filters.event_id,
                include_noisy=True,
            )
        )
        end_exclusive = filters.date_to + timedelta(days=1)
        date_from_idx = len(params) + 1
        date_to_idx = len(params) + 2
        params.extend([filters.date_from, end_exclusive])
        noisy_names = sorted(NOISY_EVENT_NAMES)
        placeholders = ", ".join(
            f"${len(params) + 1 + i}" for i in range(len(noisy_names))
        )
        params.extend(noisy_names)
        val = await self._pool.fetchval(
            f"""
            select count(*)::int
            from admin_event_log l
            left join users u on u.id = l.user_id
            where {where}
              and l.created_at >= ${date_from_idx} and l.created_at < ${date_to_idx}
              and l.event_name in ({placeholders})
            """,
            *params,
        )
        return int(val or 0)

    def catalog_for_template(self) -> list[dict]:
        return [
            {
                "name": e.name,
                "label": e.label,
                "group": e.group,
                "group_label": EVENT_GROUPS[e.group],
            }
            for e in EVENT_CATALOG
        ]

    def _build_where(self, filters: ActivityFilters) -> tuple[str, list]:
        clauses = ["true"]
        params: list = []
        idx = 1

        if filters.user_id:
            clauses.append(f"l.user_id = ${idx}")
            params.append(filters.user_id)
            idx += 1

        if filters.username:
            clauses.append(
                f"(u.username ilike ${idx} or u.first_name ilike ${idx} "
                f"or cast(u.telegram_id as text) = ${idx + 1})"
            )
            pattern = f"%{filters.username}%"
            params.extend([pattern, filters.username.strip()])
            idx += 2

        if filters.event_name:
            clauses.append(f"l.event_name = ${idx}")
            params.append(filters.event_name)
            idx += 1
        elif filters.event_group:
            names = GROUP_EVENT_NAMES.get(filters.event_group, [])
            if names:
                placeholders = ", ".join(f"${idx + i}" for i in range(len(names)))
                clauses.append(f"l.event_name in ({placeholders})")
                params.extend(names)
                idx += len(names)

        if filters.event_id:
            clauses.append(f"l.properties->>'event_id' = ${idx}")
            params.append(str(filters.event_id))
            idx += 1

        if not filters.include_noisy:
            noisy = sorted(NOISY_EVENT_NAMES)
            placeholders = ", ".join(f"${idx + i}" for i in range(len(noisy)))
            clauses.append(f"l.event_name not in ({placeholders})")
            params.extend(noisy)
            idx += len(noisy)

        return " and ".join(clauses), params

    @staticmethod
    def _row_to_activity(row: asyncpg.Record) -> ActivityRow:
        user_id = row["user_id"]
        display = None
        if user_id:
            parts = [row["first_name"], row["last_name"]]
            name = " ".join(p for p in parts if p).strip()
            if row["username"]:
                display = f"@{row['username']}" if not name else f"{name} (@{row['username']})"
            elif name:
                display = name
            else:
                display = str(row["telegram_id"])

        linked = None
        raw = row["linked_event_id_raw"]
        if raw:
            try:
                linked = UUID(raw)
            except ValueError:
                linked = None

        event_name = row["event_name"]
        return ActivityRow(
            id=row["id"],
            created_at=row["created_at"],
            event_name=event_name,
            event_label=EVENT_LABELS.get(event_name, event_name),
            user_id=user_id,
            user_display=display,
            properties=row["properties"],
            linked_event_id=linked,
        )

    @staticmethod
    def _parse_date(raw: str | None) -> date | None:
        if not raw:
            return None
        try:
            return date.fromisoformat(raw)
        except ValueError:
            return None
