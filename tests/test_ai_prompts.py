from app.services.ai.prompts import GENERATE_BATCH_SYSTEM, GENERATION_SCORING_CALIBRATION


def test_generation_prompt_requests_wider_score_spread():
    assert "GENERATION_SCORING_CALIBRATION" not in GENERATE_BATCH_SYSTEM
    assert GENERATION_SCORING_CALIBRATION.splitlines()[0].startswith("Scoring for ai_generated")
    assert "|ai_score| >= 4" in GENERATE_BATCH_SYSTEM
    assert "|ai_score| >= 6" in GENERATE_BATCH_SYSTEM
    assert "keep scores modest" not in GENERATE_BATCH_SYSTEM.lower()
