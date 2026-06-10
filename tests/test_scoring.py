from app.utils.scoring import calculate_final_community_score, get_ai_user_weights


def test_weights_at_thresholds():
    assert get_ai_user_weights(0) == (1.0, 0.0)
    assert get_ai_user_weights(10) == (0.9, 0.1)
    assert get_ai_user_weights(1000) == (0.0, 1.0)


def test_final_score_no_ratings():
    assert calculate_final_community_score(5.0, None, 0) == 5.0


def test_final_score_with_ratings():
    score = calculate_final_community_score(10.0, 0.0, 10)
    assert score == 9.0  # 10*0.9 + 0*0.1
