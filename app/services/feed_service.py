import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING
from uuid import UUID

from app.config import settings
from app.db.repositories.batches import BatchesRepository
from app.db.repositories.events import EventsRepository
from app.db.repositories.friendships import FriendshipsRepository
from app.db.repositories.impressions import ImpressionsRepository
from app.schemas.events import EventForRating
from app.schemas.feed import FeedEventCandidate
from app.services.ai_generation_service import AIGenerationService
from app.utils.feed_priority import (
    FEED_TIER_FRIEND,
    FEED_TIER_USER,
    source_priority,
)

if TYPE_CHECKING:
    from app.services.analytics_service import AnalyticsService

logger = logging.getLogger(__name__)


@dataclass
class FeedStart:
    batch_id: UUID
    batch_size: int
    is_new_batch: bool
    event: EventForRating | None


class FeedService:
    def __init__(
        self,
        events_repo: EventsRepository,
        impressions_repo: ImpressionsRepository,
        batches_repo: BatchesRepository,
        friendships_repo: FriendshipsRepository,
        ai_generation_service: AIGenerationService | None = None,
        analytics_service: "AnalyticsService | None" = None,
    ) -> None:
        self._events = events_repo
        self._impressions = impressions_repo
        self._batches = batches_repo
        self._friendships = friendships_repo
        self._ai_generation = ai_generation_service
        self._analytics = analytics_service

    def _track(self, event_name: str, user_id: UUID, **properties) -> None:
        if self._analytics:
            self._analytics.track_background(event_name, user_id, **properties)

    def _track_shown_batch(
        self,
        user_id: UUID,
        batch_id: UUID,
        event_ids: list[UUID],
        feed_tiers: list[int],
    ) -> None:
        if not self._analytics:
            return
        rows = [
            (
                "event_shown",
                user_id,
                {
                    "event_id": str(event_id),
                    "batch_id": str(batch_id),
                    "feed_tier": tier,
                },
            )
            for event_id, tier in zip(event_ids, feed_tiers)
        ]
        self._analytics.track_many_background(rows)

    async def start_or_resume(self, user_id: UUID, *, force_new: bool = False) -> FeedStart:
        if force_new:
            active_id = await self._batches.get_active_batch(user_id)
            if active_id:
                await self._batches.complete_batch(active_id)

        batch_id = None if force_new else await self._batches.get_active_batch(user_id)
        is_new_batch = False

        if batch_id:
            await self._sync_user_events_into_batch(user_id, batch_id)
            event_id = await self._impressions.get_next_shown(user_id, batch_id)
            if event_id:
                event = await self._events.get_for_rating(event_id)
                remaining = await self._batches.count_remaining(user_id, batch_id)
                self._track(
                    "feed_started",
                    user_id,
                    batch_id=str(batch_id),
                    is_new_batch=False,
                    batch_size=remaining,
                )
                return FeedStart(batch_id, remaining, False, event)
            self._track(
                "batch_completed",
                user_id,
                batch_id=str(batch_id),
            )
            await self._batches.complete_batch(batch_id)

        candidates = await self._fetch_or_generate(user_id)

        if not candidates:
            self._track("feed_empty", user_id)
            return FeedStart(UUID(int=0), 0, False, None)

        event_ids = [c.id for c in candidates]
        priorities = [source_priority(c.feed_tier, c.created_at) for c in candidates]
        feed_tiers = [c.feed_tier for c in candidates]

        batch_id = await self._batches.create_batch(
            user_id,
            settings.batch_size,
            len(event_ids),
        )
        await self._impressions.create_batch_impressions(
            user_id,
            batch_id,
            event_ids,
            priorities,
            feed_tiers,
        )
        is_new_batch = True

        self._track(
            "batch_created",
            user_id,
            batch_id=str(batch_id),
            requested_size=settings.batch_size,
            actual_size=len(event_ids),
        )
        self._track(
            "feed_started",
            user_id,
            batch_id=str(batch_id),
            is_new_batch=True,
            batch_size=len(event_ids),
        )
        self._track_shown_batch(user_id, batch_id, event_ids, feed_tiers)

        event = await self._events.get_for_rating(event_ids[0])
        return FeedStart(batch_id, len(event_ids), is_new_batch, event)

    async def on_user_event_created(self, event_id: UUID, author_id: UUID) -> None:
        meta = await self._events.get_feed_meta(event_id)
        if not meta:
            return

        friend_ids = set(await self._friendships.list_friend_user_ids(author_id))
        injected = 0

        for viewer_id in friend_ids:
            if await self._inject_event_for_viewer(
                viewer_id, event_id, meta, FEED_TIER_FRIEND
            ):
                injected += 1

        for viewer_id in await self._batches.list_users_with_active_batches():
            if viewer_id == author_id or viewer_id in friend_ids:
                continue
            if await self._inject_event_for_viewer(
                viewer_id, event_id, meta, FEED_TIER_USER
            ):
                injected += 1

        if injected:
            logger.info(
                "Injected event %s into %s active feeds (author=%s)",
                event_id,
                injected,
                author_id,
            )

    async def _inject_event_for_viewer(
        self,
        viewer_id: UUID,
        event_id: UUID,
        meta: FeedEventCandidate,
        feed_tier: int,
    ) -> bool:
        if await self._impressions.has_impression(viewer_id, event_id):
            return False
        if not await self._events.is_visible_to_user(viewer_id, event_id):
            return False

        batch_id = await self._batches.get_active_batch(viewer_id)
        if not batch_id:
            return False

        if await self._impressions.is_in_batch(batch_id, event_id):
            return False

        priority = source_priority(feed_tier, meta.created_at)
        injected = await self._impressions.inject_into_batch(
            viewer_id, batch_id, event_id, priority, feed_tier
        )
        if injected:
            self._track(
                "event_injected_into_batch",
                viewer_id,
                event_id=str(event_id),
                batch_id=str(batch_id),
                feed_tier=feed_tier,
            )
        return injected

    async def _sync_user_events_into_batch(self, user_id: UUID, batch_id: UUID) -> int:
        pending = await self._events.list_user_events_for_injection(
            user_id, batch_id
        )
        synced = 0
        for candidate in pending:
            if await self._impressions.inject_into_batch(
                user_id,
                batch_id,
                candidate.id,
                source_priority(candidate.feed_tier, candidate.created_at),
                candidate.feed_tier,
            ):
                synced += 1
        return synced

    def schedule_pool_refill(self, user_id: UUID) -> None:
        if self._ai_generation:
            self._ai_generation.schedule_pool_refill(user_id)

    async def _fetch_or_generate(self, user_id: UUID) -> list[FeedEventCandidate]:
        candidates = await self._events.fetch_available_candidates(
            user_id,
            settings.batch_size,
            settings.under_rated_threshold,
        )
        if not self._ai_generation:
            return candidates

        if len(candidates) == 0:
            await self._ai_generation.ensure_pool_for_user(user_id, minimum=1)
            return await self._events.fetch_available_candidates(
                user_id,
                settings.batch_size,
                settings.under_rated_threshold,
            )

        if len(candidates) < settings.ai_generation_min_available:
            self.schedule_pool_refill(user_id)
        return candidates

    async def get_event(self, event_id: UUID) -> EventForRating | None:
        return await self._events.get_for_rating(event_id)

    async def get_next_in_batch(self, user_id: UUID, batch_id: UUID) -> EventForRating | None:
        await self._sync_user_events_into_batch(user_id, batch_id)
        event_id = await self._impressions.get_next_shown(user_id, batch_id)
        if not event_id:
            self._track(
                "batch_completed",
                user_id,
                batch_id=str(batch_id),
            )
            await self._batches.complete_batch(batch_id)
            return None
        return await self._events.get_for_rating(event_id)
