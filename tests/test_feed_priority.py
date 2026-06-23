from datetime import datetime, timezone

from app.utils.feed_priority import source_priority


def test_source_priority_exceeds_int32_for_recent_events():
    created_at = datetime(2026, 6, 10, tzinfo=timezone.utc)
    for tier in range(4):
        value = source_priority(tier, created_at)
        assert abs(value) > 2_147_483_647
