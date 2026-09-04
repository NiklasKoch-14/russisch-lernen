import pytest

from app.content.loader import load_course
from app.course import review
from app.repositories import lexeme_srs_repo
from app.repositories.lexeme_srs_repo import SrsState
from tests.content_factory import write_course

TODAY = "2026-09-10"


@pytest.fixture
def course(tmp_path):
    return load_course(write_course(tmp_path))


def _due(conn, lexeme_id, form_key, due_date="2026-09-01"):
    lexeme_srs_repo.upsert_state(
        conn,
        SrsState(
            lexeme_id=lexeme_id,
            form_key=form_key,
            interval_days=1.0,
            ease_factor=2.5,
            repetitions=1,
            due_date=due_date,
        ),
    )


def test_empty_round_when_nothing_is_due(conn, course):
    assert review.build_review_round(conn, course, today=TODAY)["left"] == []


def test_round_shows_due_forms_and_glosses(conn, course):
    _due(conn, "delat", "prs.1sg")
    _due(conn, "ja", "nom")
    payload = review.build_review_round(conn, course, today=TODAY)
    assert {item["text"] for item in payload["left"]} == {"де́лаю", "я"}
    assert {item["gloss_de"] for item in payload["right"]} == {"machen, tun", "ich"}


def test_round_skips_forms_that_are_no_longer_in_the_lexicon(conn, course):
    _due(conn, "gone", "nom")
    _due(conn, "ja", "nom")
    assert len(review.build_review_round(conn, course, today=TODAY)["left"]) == 1


def test_correct_round_marks_every_form_as_passed(conn, course):
    _due(conn, "delat", "prs.1sg")
    _due(conn, "ja", "nom")
    payload = review.build_review_round(conn, course, today=TODAY)
    pairs = _correct_pairs(course, payload)
    result = review.grade_review_round(conn, course, today=TODAY, submission={"pairs": pairs})
    assert result["correct_count"] == 2
    assert lexeme_srs_repo.get_state(conn, lexeme_id="ja", form_key="nom").due_date > TODAY


def _correct_pairs(course, payload):
    return [
        [
            item["index"],
            next(
                other["index"]
                for other in payload["right"]
                if other["gloss_de"] == course.gloss(tuple(item["ref"].split(":")))
            ),
        ]
        for item in payload["left"]
    ]


def test_swapped_pairs_are_both_wrong(conn, course):
    _due(conn, "delat", "prs.1sg")
    _due(conn, "ja", "nom")
    payload = review.build_review_round(conn, course, today=TODAY)
    correct = _correct_pairs(course, payload)
    swapped = [[correct[0][0], correct[1][1]], [correct[1][0], correct[0][1]]]
    result = review.grade_review_round(conn, course, today=TODAY, submission={"pairs": swapped})
    assert result["correct_count"] == 0
    assert all(item["correct"] is False for item in result["results"])


def test_a_single_wrong_pair_leaves_the_other_form_passed(conn, course):
    _due(conn, "delat", "prs.1sg")
    _due(conn, "ja", "nom")
    payload = review.build_review_round(conn, course, today=TODAY)
    correct = _correct_pairs(course, payload)
    result = review.grade_review_round(
        conn, course, today=TODAY, submission={"pairs": [correct[0]]}
    )
    assert result["correct_count"] == 1
    passed = next(item for item in result["results"] if item["correct"])
    missed = next(item for item in result["results"] if not item["correct"])
    passed_id, passed_key = passed["ref"].split(":")
    missed_id, missed_key = missed["ref"].split(":")
    assert lexeme_srs_repo.get_state(conn, lexeme_id=passed_id, form_key=passed_key).repetitions == 2
    assert lexeme_srs_repo.get_state(conn, lexeme_id=missed_id, form_key=missed_key).repetitions == 0


def test_round_size_is_capped(conn, course):
    _due(conn, "delat", "prs.1sg")
    _due(conn, "delat", "prs.2sg")
    _due(conn, "ja", "nom")
    assert len(review.build_review_round(conn, course, today=TODAY, size=2)["left"]) == 2
