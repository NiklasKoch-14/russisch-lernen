import copy

import pytest

from app.content.loader import load_course
from app.course import service
from app.course.presenter import (
    build_sentence_tiles,
    choose_form_options,
    dialog_reply_options,
    match_pairs_sides,
)
from app.course.service import MAX_INTERVAL_DAYS, schedule_form, unit_payload
from app.repositories import lexeme_srs_repo, progress_repo, review_repo
from app.repositories.lexeme_srs_repo import SrsState
from tests.content_factory import MINIMAL_UNIT, write_course


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


def test_unit_payload_stellt_die_neuen_woerter_vor(conn, tmp_path):
    course = load_course(write_course(tmp_path))
    payload = unit_payload(course, conn, 1)
    woerter = payload["new_words"]

    # Reihenfolge wie in new_lexemes, damit der Autor sie steuern kann.
    assert [w["id"] for w in woerter] == ["ja", "delat"]
    assert woerter[0]["gloss_de"] == "ich"
    assert woerter[1]["gloss_de"] == "machen, tun"


def test_neue_woerter_zeigen_die_nennform(conn, tmp_path):
    # Ein Verb wird im Woerterbuch als Infinitiv gefuehrt, nicht als „ich mache".
    course = load_course(write_course(tmp_path))
    woerter = {w["id"]: w for w in unit_payload(course, conn, 1)["new_words"]}
    assert woerter["delat"]["text"] == "де́лать"
    assert woerter["delat"]["translit"] == "délat'"
    assert woerter["ja"]["text"] == "я"


def test_unbekanntes_lexem_in_new_lexemes_wird_uebersprungen(conn, tmp_path):
    unit = copy.deepcopy(MINIMAL_UNIT)
    unit["new_lexemes"] = unit["new_lexemes"] + ["gibtesnicht"]
    course = load_course(write_course(tmp_path, units=[unit]))
    ids = [w["id"] for w in unit_payload(course, conn, 1)["new_words"]]
    assert "gibtesnicht" not in ids


def test_wiederholung_bewertet_und_plant_fort(conn, tmp_path):
    course = load_course(write_course(tmp_path))
    exercise = course.units[1].exercises[1]
    options = choose_form_options(course, exercise)
    richtige = options.index(exercise.answer)

    outcome = service.submit_review_exercise(
        conn,
        course,
        unit_id=1,
        exercise_id="1-2",
        submission={"option_index": richtige},
        today="2026-01-02",
    )
    assert outcome.correct is True
    assert lexeme_srs_repo.get_state(conn, lexeme_id="delat", form_key="prs.1sg") is not None


def test_wiederholung_ruehrt_den_einheiten_fortschritt_nicht_an(conn, tmp_path):
    # Die wichtigste Zusage: eine falsche Wiederholung darf eine abgeschlossene
    # Einheit nicht wieder aufreissen und ihre Statistik nicht verfaelschen.
    course = load_course(write_course(tmp_path))
    progress_repo.bump_progress(conn, unit_id=1, correct=True)
    vorher = progress_repo.get_progress(conn, 1)

    service.submit_review_exercise(
        conn,
        course,
        unit_id=1,
        exercise_id="1-2",
        submission={"option_index": 99},
        today="2026-01-02",
    )

    nachher = progress_repo.get_progress(conn, 1)
    assert (nachher.correct_count, nachher.total_count, nachher.status) == (
        vorher.correct_count,
        vorher.total_count,
        vorher.status,
    )
    assert progress_repo.attempt_count(conn, 1) == 0, "kein Versuch darf protokolliert werden"


def test_wiederholung_vermerkt_jede_geuebte_form(conn, tmp_path):
    course = load_course(write_course(tmp_path))
    service.submit_review_exercise(
        conn,
        course,
        unit_id=1,
        exercise_id="1-2",
        submission={"option_index": 99},
        today="2026-01-02",
    )
    assert review_repo.count_on(conn, "2026-01-02") == 1
    assert review_repo.count_on(conn, "2026-01-03") == 0


def test_wiederholung_lehnt_eine_fremde_aufgabe_ab(conn, tmp_path):
    course = load_course(write_course(tmp_path))
    with pytest.raises(KeyError):
        service.submit_review_exercise(
            conn, course, unit_id=1, exercise_id="gibtesnicht", submission={}
        )


def _units_sharing_a_primer():
    """Zwei Einheiten, die denselben Primer benutzen — die erste soll ihn aufklappen."""
    first = copy.deepcopy(MINIMAL_UNIT)
    first["grammar_focus"]["primer"] = "akkusativ"
    second = copy.deepcopy(first)
    second["id"] = 2
    return [first, second]


def test_unit_payload_ohne_primer_liefert_none(conn, course):
    assert unit_payload(course, conn, 1)["primer"] is None


def test_unit_payload_liefert_den_primer_text(conn, tmp_path):
    course = load_course(write_course(tmp_path, units=_units_sharing_a_primer()))
    primer = unit_payload(course, conn, 1)["primer"]
    assert primer["title_de"] == "Was ist der Akkusativ?"
    assert "direkten Objekts" in primer["text_de"]


def test_primer_ist_in_der_ersten_einheit_aufgeklappt(conn, tmp_path):
    course = load_course(write_course(tmp_path, units=_units_sharing_a_primer()))
    assert unit_payload(course, conn, 1)["primer"]["first_use"] is True


def test_primer_ist_in_spaeteren_einheiten_zugeklappt(conn, tmp_path):
    course = load_course(write_course(tmp_path, units=_units_sharing_a_primer()))
    assert unit_payload(course, conn, 2)["primer"]["first_use"] is False


def test_scheduling_survives_a_huge_stored_interval(conn):
    """Eine Datenbank aus der Zeit ohne Deckel darf die Antwort nicht umbringen.

    Genau das ist passiert: `POST /api/game/scenes/bar-02/turns/1` antwortete
    mit 500, weil `date + timedelta(days=…)` über das Jahr 9999 hinauslief.
    """
    lexeme_srs_repo.upsert_state(
        conn,
        SrsState(
            lexeme_id="eto",
            form_key="base",
            interval_days=9_000_000.0,
            ease_factor=2.5,
            repetitions=30,
            due_date="9999-12-31",
        ),
    )

    schedule_form(conn, ("eto", "base"), correct=True, today="2026-09-09")

    state = lexeme_srs_repo.get_state(conn, lexeme_id="eto", form_key="base")
    assert state.interval_days <= MAX_INTERVAL_DAYS
    assert state.due_date < "9999-01-01"
