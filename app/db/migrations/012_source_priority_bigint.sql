-- source_priority uses tier * 1e12 - timestamp_ms and exceeds int32 range.
alter table event_impressions
  alter column source_priority type bigint using source_priority::bigint;
