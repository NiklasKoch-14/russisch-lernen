"""Die beiden Routen des Hören-Tabs."""

import pytest
from fastapi.testclient import TestClient

from app.dependencies import get_course, get_db
from app.main import app
from app.repositories.profile_repo import get_or_create_profile, update_profile
from tests.test_listening_service import _dialog, _lexeme

from app.content.models import Course


@pytest.fixture
def course() -> Course:
    return Course(
        language="russian",
        lexemes={"da": _lexeme("da", "да", "da"), "net": _lexeme("net", "нет", "net")},
        units={},
        dialogs={1: _dialog(1, min_unit=5), 2: _dialog(2, min_unit=40)},
    )


@pytest.fixture
def client(course, tmp_path):
    from app.db import get_connection, init_db

    path = str(tmp_path / "routes.db")
    init_db(path)
    conn = get_connection(path)
    get_or_create_profile(conn, "russian")

    app.dependency_overrides[get_course] = lambda: course
    app.dependency_overrides[get_db] = lambda: conn
    yield TestClient(app), conn
    app.dependency_overrides.clear()
    conn.close()


def test_ohne_fortschritt_nennt_die_route_die_naechste_einheit(client):
    api, _ = client
    body = api.get("/api/listening/next").json()
    assert body["dialog_id"] is None
    assert body["next_unit"] == 5


def test_liefert_ein_freigeschaltetes_gespraech_ohne_loesung(client):
    api, conn = client
    update_profile(conn, placement_unit=10)
    body = api.get("/api/listening/next").json()
    assert body["dialog_id"] == 1
    assert body["seed"]
    assert len(body["lines"]) == 3
    assert body["lines"][0]["text"] == "да"
    assert sorted(body["options_de"]) == ["Falsch A.", "Falsch B.", "Falsch C.", "Richtig."]
    assert "correct_index" not in body
    assert "title_de" not in body


def test_die_richtige_antwort_deckt_titel_und_uebersetzungen_auf(client, course):
    api, conn = client
    update_profile(conn, placement_unit=10)
    body = api.get("/api/listening/next").json()
    richtig = body["options_de"].index("Richtig.")

    result = api.post(
        "/api/listening/1/answer", json={"seed": body["seed"], "option_index": richtig}
    ).json()
    assert result["correct"] is True
    assert result["correct_index"] == richtig
    assert result["title_de"] == "Gespräch 1"
    assert result["translations_de"] == ["Ja.", "Nein.", "Ja."]


def test_eine_falsche_antwort_nennt_die_richtige_stelle(client):
    api, conn = client
    update_profile(conn, placement_unit=10)
    body = api.get("/api/listening/next").json()
    richtig = body["options_de"].index("Richtig.")
    falsch = (richtig + 1) % len(body["options_de"])

    result = api.post(
        "/api/listening/1/answer", json={"seed": body["seed"], "option_index": falsch}
    ).json()
    assert result["correct"] is False
    assert result["correct_index"] == richtig


def test_die_antwort_wird_vermerkt(client):
    api, conn = client
    update_profile(conn, placement_unit=10)
    body = api.get("/api/listening/next").json()
    api.post("/api/listening/1/answer", json={"seed": body["seed"], "option_index": 0})
    rows = conn.execute("SELECT dialog_id FROM listening_runs").fetchall()
    assert [row["dialog_id"] for row in rows] == [1]


def test_ein_unbekanntes_gespraech_ist_ein_404(client):
    api, _ = client
    assert api.post("/api/listening/99/answer", json={"seed": "s", "option_index": 0}).status_code == 404


def test_ein_bestimmtes_gespraech_laesst_sich_anfordern(client):
    # Die Startseite verlinkt ein Gespräch, das zum Gelernten passt.
    api, conn = client
    update_profile(conn, placement_unit=50)
    assert api.get("/api/listening/next?dialog_id=2").json()["dialog_id"] == 2
    assert api.get("/api/listening/next?dialog_id=1").json()["dialog_id"] == 1


def test_ein_gesperrtes_gespraech_wird_durch_das_naechste_ersetzt(client):
    api, conn = client
    update_profile(conn, placement_unit=10)
    assert api.get("/api/listening/next?dialog_id=2").json()["dialog_id"] == 1
