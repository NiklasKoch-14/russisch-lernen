import pytest
from fastapi.testclient import TestClient

from app.content.loader import load_course
from app.course.presenter import build_sentence_tiles
from app.db import get_connection
from app.dependencies import get_course, get_db
from app.main import app
from tests.content_factory import write_course


@pytest.fixture
def course(tmp_path):
    return load_course(write_course(tmp_path / "content"))


@pytest.fixture
def client(db_path, course):
    def override_db():
        conn = get_connection(db_path)
        try:
            yield conn
        finally:
            conn.close()

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_course] = lambda: course
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_course_endpoint_lists_stages(client):
    response = client.get("/api/course")
    assert response.status_code == 200
    assert response.json()["stages"][0]["units"][0]["id"] == 1


def test_unit_endpoint_returns_exercises_without_solutions(client):
    body = client.get("/api/units/1").json()
    assert body["grammar_focus"]["title_de"]
    assert len(body["exercises"]) == 4
    assert "solution" not in body["exercises"][0]


def test_unit_endpoint_404s_for_unknown_unit(client):
    assert client.get("/api/units/999").status_code == 404


def test_answer_endpoint_grades_and_reports_progress(client, course):
    exercise = course.units[1].exercises[0]
    tiles = build_sentence_tiles(course, exercise)
    body = client.post(
        "/api/units/1/answer",
        json={
            "exercise_id": exercise.id,
            "submission": {"tile_indices": [tiles.index(ref) for ref in exercise.solution]},
        },
    ).json()
    assert body["correct"] is True
    assert body["solution_text"] == "я де́лаю"
    assert body["unit_completed"] is False


def test_answer_endpoint_404s_for_unknown_exercise(client):
    response = client.post("/api/units/1/answer", json={"exercise_id": "nope", "submission": {}})
    assert response.status_code == 404


def test_screening_start_returns_first_probe(client):
    body = client.post("/api/screening/start").json()
    assert body["finished"] is False
    assert body["probe"]["index"] == 0


def test_screening_answer_finishes_and_persists_placement(client):
    body = client.post("/api/screening/answer", json={"answers": [0]}).json()
    assert body["finished"] is True
    assert body["placement_unit"] == 1
    assert client.get("/api/profile").json()["placement_unit"] == 1


def test_review_due_is_empty_initially(client):
    assert client.get("/api/review/due").json()["left"] == []


def test_profile_patch_toggles_transliteration(client):
    body = client.patch("/api/profile", json={"show_transliteration": False}).json()
    assert body["show_transliteration"] is False


def test_explain_falls_back_to_the_unit_rule_when_ollama_fails(client):
    from app.dependencies import get_ollama

    class Boom:
        def chat(self, messages):
            raise RuntimeError("ollama down")

    app.dependency_overrides[get_ollama] = lambda: Boom()
    body = client.post(
        "/api/explain", json={"unit_id": 1, "exercise_id": "1-1", "chosen_text": "де́лает я"}
    ).json()
    assert body["source"] == "rule"
    assert body["explanation_de"] == "Die Endung zeigt, wer handelt."
