from app.utils.scoring import (
    build_community_score_breakdown,
    calculate_final_community_score,
    get_ai_user_weights,
)


def test_weights_at_thresholds():
    assert get_ai_user_weights(0) == (1.0, 0.0)
    assert get_ai_user_weights(10) == (0.9, 0.1)
    assert get_ai_user_weights(1000) == (0.0, 1.0)


def test_final_score_no_ratings():
    assert calculate_final_community_score(5.0, None, 0) == 5.0


def test_final_score_with_ratings():
    score = calculate_final_community_score(10.0, 0.0, 10)
    assert score == 9.0  # 10*0.9 + 0*0.1


def test_score_breakdown_stores_weights():
    breakdown = build_community_score_breakdown(5.0, -2.0, 10)
    assert breakdown.ai_weight == 0.9
    assert breakdown.user_weight == 0.1
    assert breakdown.final_community_score == 4.3


def test_score_breakdown_ai_only():
    breakdown = build_community_score_breakdown(-9.0, None, 0)
    assert breakdown.is_ai_only()
    assert breakdown.ai_weight == 1.0
    assert breakdown.final_community_score == -9.0
