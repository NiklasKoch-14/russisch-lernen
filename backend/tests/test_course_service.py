import pytest

from app.content.loader import load_course
from app.course import service
from app.course.presenter import (
    build_sentence_tiles,
    choose_form_options,
    dialog_reply_options,
    match_pairs_sides,
)
from app.repositories import lexeme_srs_repo, progress_repo
from tests.content_factory import write_course


@pytest.fixture
def course(tmp_path):
    return load_course(write_course(tmp_path))


def _correct_build_submission(course):
    exercise = course.units[1].exercises[0]
    tiles = build_sentence_tiles(course, exercise)
    return exercise.id, {"tile_indices": [tiles.index(ref) for ref in exercise.solution]}


def _submission_for(course, exercise):
    if exercise.type == "build_sentence":
        tiles = build_sentence_tiles(course, exercise)
        return {"tile_indices": [tiles.index(ref) for ref in exercise.solution]}
    if exercise.type == "choose_form":
        options = choose_form_options(course, exercise)
        return {"option_index": options.index(exercise.answer)}
    if exercise.type == "match_pairs":
        left, right = match_pairs_sides(course, exercise)
        return {"pairs": [[index, right.index(ref)] for index, ref in enumerate(left)]}
    order = dialog_reply_options(course, exercise)
    return {"option_index": order.index(exercise.correct_index)}


def test_correct_answer_reports_success_and_counts(conn, course):
    exercise_id, submission = _correct_build_submission(course)
    outcome = service.submit_answer(
        conn, course, unit_id=1, exercise_id=exercise_id, submission=submission
    )
    assert outcome.correct is True
    assert (outcome.correct_count, outcome.total_count) == (1, 1)


def test_wrong_answer_returns_solution_and_explanation(conn, course):
    outcome = service.submit_answer(
        conn, course, unit_id=1, exercise_id="1-1", submission={"tile_indices": [0]}
    )
    assert outcome.correct is False
    assert outcome.solution_text == "я де́лаю"
    assert outcome.explanation_de


def test_answer_is_recorded_as_attempt(conn, course):
    service.submit_answer(
        conn, course, unit_id=1, exercise_id="1-1", submission={"tile_indices": [0]}
    )
    assert progress_repo.attempt_count(conn, 1) == 1


def test_correct_answer_schedules_trained_forms_for_review(conn, course):
    exercise_id, submission = _correct_build_submission(course)
    service.submit_answer(
        conn,
        course,
        unit_id=1,
        exercise_id=exercise_id,
        submission=submission,
        today="2026-09-04",
    )
    state = lexeme_srs_repo.get_state(conn, lexeme_id="delat", form_key="prs.1sg")
    assert state is not None
    assert state.repetitions == 1
    assert state.due_date > "2026-09-04"


def test_wrong_answer_makes_trained_forms_due_again_immediately(conn, course):
    service.submit_answer(
        conn,
        course,
        unit_id=1,
        exercise_id="1-1",
        submission={"tile_indices": [0]},
        today="2026-09-04",
    )
    state = lexeme_srs_repo.get_state(conn, lexeme_id="delat", form_key="prs.1sg")
    assert state.repetitions == 0
    assert state.due_date == "2026-09-05"


def test_unit_completes_only_after_every_exercise_was_right_once(conn, course):
    outcomes = [
        service.submit_answer(
            conn,
            course,
            unit_id=1,
            exercise_id=exercise.id,
            submission=_submission_for(course, exercise),
        )
        for exercise in course.units[1].exercises
    ]
    assert [outcome.unit_completed for outcome in outcomes] == [False, False, False, True]
    assert progress_repo.get_progress(conn, 1).status == "completed"


def test_unknown_exercise_id_raises_key_error(conn, course):
    with pytest.raises(KeyError):
        service.submit_answer(conn, course, unit_id=1, exercise_id="nope", submission={})


def test_unit_payload_contains_rule_and_exercises_without_solutions(conn, course):
    payload = service.unit_payload(course, conn, unit_id=1)
    assert payload["grammar_focus"]["explanation_de"]
    assert len(payload["exercises"]) == 4
    assert all("solution" not in exercise for exercise in payload["exercises"])


def test_course_overview_groups_units_by_stage(conn, course):
    overview = service.course_overview(course, conn)
    assert {stage["stage"] for stage in overview["stages"]} == {0}
    assert overview["stages"][0]["units"][0]["status"] == "not_started"


def test_course_overview_reflects_progress(conn, course):
    exercise_id, submission = _correct_build_submission(course)
    service.submit_answer(conn, course, unit_id=1, exercise_id=exercise_id, submission=submission)
    overview = service.course_overview(course, conn)
    assert overview["stages"][0]["units"][0]["status"] == "in_progress"
