from app.srs.sm2 import sm2_update


def test_first_correct_answer_sets_interval_to_one_day():
    result = sm2_update(correct=True, repetitions=0, ease_factor=2.5, interval_days=0)
    assert result.repetitions == 1
    assert result.interval_days == 1.0
    assert result.ease_factor == 2.5


def test_second_correct_answer_sets_interval_to_six_days():
    result = sm2_update(correct=True, repetitions=1, ease_factor=2.5, interval_days=1.0)
    assert result.repetitions == 2
    assert result.interval_days == 6.0


def test_third_correct_answer_multiplies_interval_by_ease_factor():
    result = sm2_update(correct=True, repetitions=2, ease_factor=2.5, interval_days=6.0)
    assert result.repetitions == 3
    assert result.interval_days == 15.0


def test_incorrect_answer_resets_repetitions_and_interval():
    result = sm2_update(correct=False, repetitions=3, ease_factor=2.5, interval_days=15.0)
    assert result.repetitions == 0
    assert result.interval_days == 1.0
    assert result.ease_factor == 2.18


def test_ease_factor_never_drops_below_1_3():
    result = sm2_update(correct=False, repetitions=0, ease_factor=1.35, interval_days=1.0)
    assert result.ease_factor >= 1.3
