import asyncio
import logging

import asyncpg

from app.services.ai_service import AIService
from app.utils.scoring import (
    SCORING_CALIBRATION_VERSION,
    build_community_score_breakdown,
)

logger = logging.getLogger(__name__)


class ScoreRecalibrationService:
    def __init__(self, pool: asyncpg.Pool, ai_service: AIService) -> None:
        self._pool = pool
        self._ai = ai_service

    async def refresh_all_community_scores(self) -> int:
        rows = await self._pool.fetch(
            """
            select
              e.id,
              e.ai_score,
              count(r.id) filter (where r.rating_scope = 'community')::int
                as community_ratings_count,
              avg(r.score) filter (where r.rating_scope = 'community')::numeric(5,2)
                as community_user_score,
              count(r.id) filter (where r.rating_scope = 'friend')::int
                as friends_ratings_count,
              avg(r.score) filter (where r.rating_scope = 'friend')::numeric(5,2)
                as friends_score
            from events e
            left join ratings r on r.event_id = e.id
            where e.is_deleted = false
            group by e.id, e.ai_score
            """
        )

        updated = 0
        for row in rows:
            breakdown = build_community_score_breakdown(
                row["ai_score"],
                row["community_user_score"],
                row["community_ratings_count"] or 0,
            )
            friends_score = (
                float(row["friends_score"]) if row["friends_ratings_count"] else None
            )
            await self._pool.execute(
                """
                update events
                set community_user_score = $2,
                    friends_score = $3,
                    final_community_score = $4,
                    community_ratings_count = $5,
                    friends_ratings_count = $6,
                    community_ai_weight = $7,
                    community_user_weight = $8,
                    updated_at = now()
                where id = $1
                """,
                row["id"],
                breakdown.community_user_score,
                friends_score,
                breakdown.final_community_score,
                row["community_ratings_count"] or 0,
                row["friends_ratings_count"] or 0,
                breakdown.ai_weight,
                breakdown.user_weight,
            )
            updated += 1

        logger.info("Refreshed community score breakdown for %s events", updated)
        return updated

    async def recalibrate_outdated_ai_scores(self, batch_limit: int = 50) -> int:
        rows = await self._pool.fetch(
            """
            select
              id,
              normalized_text,
              event_type::text as event_type,
              community_user_score,
              community_ratings_count
            from events
            where is_deleted = false
              and normalized_text is not null
              and scoring_calibration_version < $1
            order by created_at desc
            limit $2
            """,
            SCORING_CALIBRATION_VERSION,
            batch_limit,
        )
        if not rows:
            return 0

        recalibrated = 0
        for row in rows:
            text = (row["normalized_text"] or "").strip()
            if not text:
                continue

            result = await self._ai.rescore_event(text, row["event_type"])
            breakdown = build_community_score_breakdown(
                result.ai_score,
                row["community_user_score"],
                row["community_ratings_count"] or 0,
            )
            await self._pool.execute(
                """
                update events
                set ai_score = $2,
                    final_community_score = $3,
                    community_ai_weight = $4,
                    community_user_weight = $5,
                    scoring_calibration_version = $6,
                    ai_score_recalibrated_at = now(),
                    updated_at = now()
                where id = $1
                """,
                row["id"],
                result.ai_score,
                breakdown.final_community_score,
                breakdown.ai_weight,
                breakdown.user_weight,
                SCORING_CALIBRATION_VERSION,
            )
            recalibrated += 1

        remaining = await self._pool.fetchval(
            """
            select count(*)::int
            from events
            where is_deleted = false
              and normalized_text is not null
              and scoring_calibration_version < $1
            """,
            SCORING_CALIBRATION_VERSION,
        )
        logger.info(
            "Recalibrated ai_score for %s events (%s still outdated)",
            recalibrated,
            remaining or 0,
        )
        return recalibrated

    async def run_background_rescore(self) -> None:
        total = 0
        try:
            while True:
                batch = await self.recalibrate_outdated_ai_scores(batch_limit=25)
                total += batch
                if batch == 0:
                    break
                await asyncio.sleep(1)
            if total:
                logger.info("Background AI rescore complete: %s events updated", total)
        except Exception:
            logger.exception("Background AI rescore failed after %s events", total)
