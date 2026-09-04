from app.repositories import progress_repo


def test_bump_progress_creates_row_on_first_attempt(conn):
    progress = progress_repo.bump_progress(conn, unit_id=3, correct=True)
    assert progress.unit_id == 3
    assert progress.status == "in_progress"
    assert (progress.correct_count, progress.total_count) == (1, 1)


def test_bump_progress_counts_wrong_answers_in_total_only(conn):
    progress_repo.bump_progress(conn, unit_id=3, correct=True)
    progress = progress_repo.bump_progress(conn, unit_id=3, correct=False)
    assert (progress.correct_count, progress.total_count) == (1, 2)


def test_complete_unit_sets_status_and_timestamp(conn):
    progress_repo.bump_progress(conn, unit_id=3, correct=True)
    progress = progress_repo.complete_unit(conn, unit_id=3)
    assert progress.status == "completed"
    assert progress.completed_at is not None


def test_get_progress_returns_none_for_untouched_unit(conn):
    assert progress_repo.get_progress(conn, 99) is None


def test_all_progress_is_keyed_by_unit_id(conn):
    progress_repo.bump_progress(conn, unit_id=1, correct=True)
    progress_repo.bump_progress(conn, unit_id=2, correct=False)
    assert set(progress_repo.all_progress(conn)) == {1, 2}


def test_record_attempt_is_queryable(conn):
    progress_repo.record_attempt(
        conn, unit_id=1, exercise_id="1-1", correct=False, answer_json='{"tile_indices":[1,0]}'
    )
    progress_repo.record_attempt(
        conn, unit_id=1, exercise_id="1-2", correct=True, answer_json='{"option_index":0}'
    )
    assert progress_repo.attempt_count(conn, 1) == 2
