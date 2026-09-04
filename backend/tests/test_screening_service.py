import pytest

from app.content.loader import load_course
from app.repositories import profile_repo
from app.screening import service
from tests.content_factory import MINIMAL_UNIT, write_course

PROBES = [
    {
        "id": "s1",
        "prompt_de": "Welcher Buchstabe klingt wie r?",
        "options": ["Р", "П"],
        "correct_index": 0,
        "maps_to_unit": 1,
    },
    {
        "id": "s2",
        "prompt_de": "Was heißt я?",
        "options": ["ich", "du"],
        "correct_index": 0,
        "maps_to_unit": 2,
    },
    {
        "id": "s3",
        "prompt_de": "Was heißt де́лаю?",
        "options": ["ich mache", "er macht"],
        "correct_index": 0,
        "maps_to_unit": 3,
    },
]


@pytest.fixture
def course(tmp_path):
    units = [dict(MINIMAL_UNIT, id=index) for index in (1, 2, 3)]
    return load_course(write_course(tmp_path, units=units, screening=PROBES))


def test_first_probe_is_returned_without_the_answer(course):
    payload = service.probe_payload(course, 0)
    assert payload["prompt_de"].startswith("Welcher Buchstabe")
    assert payload["options"] == ["Р", "П"]
    assert payload["index"] == 0 and payload["total"] == 3
    assert "correct_index" not in payload


def test_next_step_serves_the_following_probe_after_a_correct_answer(course):
    step = service.next_step(course, [0])
    assert step["finished"] is False
    assert step["probe"]["index"] == 1


def test_next_step_continues_after_a_single_wrong_answer(course):
    step = service.next_step(course, [1])
    assert step["finished"] is False
    assert step["probe"]["index"] == 1


def test_two_consecutive_wrong_answers_end_the_screening(course):
    assert service.next_step(course, [1, 1])["finished"] is True


def test_screening_ends_after_the_last_probe(course):
    step = service.next_step(course, [0, 0, 0])
    assert step["finished"] is True
    assert step["placement_unit"] == 3


def test_placement_uses_the_last_correct_probe(course):
    assert service.placement_unit_for(course, [0, 0, 1]) == 2


def test_placement_is_at_least_unit_one(course):
    assert service.placement_unit_for(course, [1, 1]) == 1


def test_finish_screening_persists_placement_and_result(conn, course):
    unit = service.finish_screening(conn, course, [0, 0, 1])
    assert unit == 2
    assert profile_repo.get_or_create_profile(conn, "russian").placement_unit == 2
    assert conn.execute("SELECT * FROM screening_results").fetchone()["placement_unit"] == 2


def test_out_of_range_answer_counts_as_wrong(course):
    assert service.placement_unit_for(course, [99]) == 1
