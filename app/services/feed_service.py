import random
from dataclasses import dataclass
from uuid import UUID

from app.config import settings
from app.db.repositories.batches import BatchesRepository
from app.db.repositories.events import EventsRepository
from app.db.repositories.impressions import ImpressionsRepository
from app.schemas.events import EventForRating


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
    ) -> None:
        self._events = events_repo
        self._impressions = impressions_repo
        self._batches = batches_repo

    async def start_or_resume(self, user_id: UUID, *, force_new: bool = False) -> FeedStart:
        batch_id = None if force_new else await self._batches.get_active_batch(user_id)
        is_new_batch = False

        if batch_id:
            event_id = await self._impressions.get_next_shown(user_id, batch_id)
            if event_id:
                event = await self._events.get_for_rating(event_id)
                remaining = await self._batches.count_remaining(user_id, batch_id)
                return FeedStart(batch_id, remaining, False, event)
            await self._batches.complete_batch(batch_id)

        event_ids = await self._events.fetch_available_for_user(
            user_id,
            settings.batch_size,
            settings.under_rated_threshold,
        )
        random.shuffle(event_ids)

        if not event_ids:
            return FeedStart(UUID(int=0), 0, False, None)

        batch_id = await self._batches.create_batch(
            user_id,
            settings.batch_size,
            len(event_ids),
        )
        await self._impressions.create_batch_impressions(user_id, batch_id, event_ids)
        is_new_batch = True

        event = await self._events.get_for_rating(event_ids[0])
        return FeedStart(batch_id, len(event_ids), is_new_batch, event)

    async def get_event(self, event_id: UUID) -> EventForRating | None:
        return await self._events.get_for_rating(event_id)

    async def get_next_in_batch(self, user_id: UUID, batch_id: UUID) -> EventForRating | None:
        event_id = await self._impressions.get_next_shown(user_id, batch_id)
        if not event_id:
            await self._batches.complete_batch(batch_id)
            return None
        return await self._events.get_for_rating(event_id)
