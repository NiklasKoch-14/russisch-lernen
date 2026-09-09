import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.content.loader import load_course
from app.db import get_connection
from app.dependencies import get_course, get_db, get_village
from app.game.loader import load_village
from app.main import app
from tests.village_factory import MINIMAL_DIALOG, write_village


@pytest.fixture
def client(db_path):
    """Wie die `client`-Fixture in test_course_routes.py, aber mit dem echten
    Kurs und dem echten Dorf statt der synthetischen Vorlagen — die Dorf-Tests
    greifen auf echte Szenen (`bar-01`) und echte Bilder zu."""
    course = load_course(settings.content_dir, language=settings.default_language)
    village = load_village(settings.game_dir)

    def override_db():
        conn = get_connection(db_path)
        try:
            yield conn
        finally:
            conn.close()

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_course] = lambda: course
    app.dependency_overrides[get_village] = lambda: village
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_village_route_lists_the_places(client):
    response = client.get("/api/game/village")
    assert response.status_code == 200
    assert {place["id"] for place in response.json()["places"]} >= {"bar", "magazin", "shkola"}


def test_place_route_returns_its_people(client):
    response = client.get("/api/game/places/bar")
    assert response.status_code == 200
    assert response.json()["kind"] == "npcs"


def test_unknown_place_is_a_404(client):
    assert client.get("/api/game/places/nirgendwo").status_code == 404


def test_starting_a_scene_returns_a_seed(client):
    response = client.post("/api/game/places/bar/scene", json={})
    assert response.status_code == 200
    body = response.json()
    assert body["seed"]
    assert body["turn_count"] >= 2


def test_a_turn_hides_the_solution(client):
    started = client.post("/api/game/places/bar/scene", json={}).json()
    response = client.get(
        f"/api/game/scenes/{started['scene_id']}/turns/0", params={"seed": started["seed"]}
    )
    assert response.status_code == 200
    body = response.json()
    assert "solution" not in body["exercise"]
    assert body["npc_line"]["text"]


def test_a_turn_beyond_the_end_is_a_404(client):
    started = client.post("/api/game/places/bar/scene", json={}).json()
    response = client.get(
        f"/api/game/scenes/{started['scene_id']}/turns/99", params={"seed": started["seed"]}
    )
    assert response.status_code == 404


def test_a_turn_of_a_scene_with_an_unknown_npc_is_a_404_not_a_500(db_path, tmp_path):
    # Der Lader prueft Szenen nicht gegen die Personenliste (nur `make validate`
    # tut das) — eine Szene kann also auf eine nicht existierende Person zeigen.
    # Die Route muss das trotzdem sauber als 404 melden statt mit einem
    # unbehandelten KeyError abzubrechen.
    course = load_course(settings.content_dir, language=settings.default_language)
    broken_scene = {**MINIMAL_DIALOG, "npc": "geist"}
    village = load_village(write_village(tmp_path, scenes=[broken_scene]))

    def override_db():
        conn = get_connection(db_path)
        try:
            yield conn
        finally:
            conn.close()

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_course] = lambda: course
    app.dependency_overrides[get_village] = lambda: village
    try:
        response = TestClient(app).get(
            f"/api/game/scenes/{broken_scene['id']}/turns/0", params={"seed": "s1"}
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    # Die Meldung nennt nicht nur die Id, sondern sagt auch, was ihr fehlt —
    # sonst steht im Fehler nur ein nacktes Wort wie "geist".
    detail = response.json()["detail"]
    assert "geist" in detail
    assert "Person" in detail


def test_starting_a_scene_with_an_unknown_npc_is_a_404_not_a_500(db_path, tmp_path):
    # Derselbe kaputte Inhalt beim Betreten des Ortes: auch hier darf kein
    # unbehandelter KeyError durchschlagen.
    course = load_course(settings.content_dir, language=settings.default_language)
    broken_scene = {**MINIMAL_DIALOG, "npc": "geist"}
    village = load_village(write_village(tmp_path, scenes=[broken_scene]))

    def override_db():
        conn = get_connection(db_path)
        try:
            yield conn
        finally:
            conn.close()

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_course] = lambda: course
    app.dependency_overrides[get_village] = lambda: village
    try:
        response = TestClient(app).post(
            f"/api/game/places/{broken_scene['place']}/scene", json={}
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    detail = response.json()["detail"]
    assert "geist" in detail
    assert "Person" in detail


def test_answering_a_turn_grades_it(client):
    started = client.post("/api/game/places/bar/scene", json={}).json()
    response = client.post(
        f"/api/game/scenes/{started['scene_id']}/turns/0",
        json={"seed": started["seed"], "submission": {"tile_indices": []}},
    )
    assert response.status_code == 200
    assert response.json()["correct"] is False
    assert response.json()["npc_reaction"]["text"]


def test_art_route_serves_the_village_map(client):
    response = client.get("/api/game/art/village")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("image/svg+xml")


def test_art_route_refuses_to_escape_the_directory(client):
    assert client.get("/api/game/art/..%2F..%2Fetc%2Fpasswd").status_code == 404
