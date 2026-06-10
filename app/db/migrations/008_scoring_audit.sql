alter table events
  add column if not exists community_ai_weight numeric(4,3),
  add column if not exists community_user_weight numeric(4,3),
  add column if not exists scoring_calibration_version integer not null default 1,
  add column if not exists ai_score_recalibrated_at timestamptz;
