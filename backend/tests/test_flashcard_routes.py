"""Die beiden Routen der Karteikarten."""

import pytest
from fastapi.testclient import TestClient

from app.dependencies import get_course, get_db
from app.main import app
from app.repositories.profile_repo import get_or_create_profile, update_profile
from tests.test_flashcards import NOMEN, VERBEN, _lexeme, _unit

from app.content.models import Course, Form, Lexeme


@pytest.fixture
def course() -> Course:
    lexemes = {
        **{k: _lexeme(k, *v) for k, v in NOMEN.items()},
        **{k: _lexeme(k, *v, pos="verb") for k, v in VERBEN.items()},
        "bu_r": Lexeme(
            id="bu_r", lemma="Р р", pos="letter", gloss_de="klingt wie r",
            forms={"base": Form(text="Р р", translit="r")},
        ),
    }
    units = {
        1: _unit(1, ["bu_r"]),
        2: _unit(2, ["khleb", "syr", "butylka", "chashka"]),
        3: _unit(3, ["paket", "kniga", "pit", "govorit"]),
    }
    return Course(language="russian", lexemes=lexemes, units=units)


@pytest.fixture
def client(course, tmp_path):
    from app.db import get_connection, init_db

    path = str(tmp_path / "karten-routen.db")
    init_db(path)
    conn = get_connection(path)
    get_or_create_profile(conn, "russian")

    app.dependency_overrides[get_course] = lambda: course
    app.dependency_overrides[get_db] = lambda: conn
    yield TestClient(app), conn
    app.dependency_overrides.clear()
    conn.close()


def test_ohne_gelernte_woerter_kommt_ein_leerer_stapel(client):
    api, _ = client
    body = api.get("/api/flashcards/round").json()
    assert body["cards"] == []
    assert body["known_words"] == 0


def test_liefert_karten_ohne_loesung(client):
    api, conn = client
    update_profile(conn, placement_unit=4)
    body = api.get("/api/flashcards/round", params={"direction": "ru_de"}).json()

    assert body["seed"]
    assert body["known_words"] == 8
    assert len(body["cards"]) == 8
    karte = body["cards"][0]
    assert karte["direction"] == "ru_de"
    assert len(karte["options_de"]) == 3
    assert "correct_index" not in karte


def test_richtige_antwort_nennt_wort_und_bedeutung(client, course):
    api, conn = client
    update_profile(conn, placement_unit=4)
    body = api.get("/api/flashcards/round", params={"direction": "ru_de"}).json()
    karte = body["cards"][0]
    lexeme = course.lexemes[karte["lexeme_id"]]
    index = karte["options_de"].index(lexeme.gloss_de)

    result = api.post(
        "/api/flashcards/answer",
        json={"lexeme_id": karte["lexeme_id"], "seed": body["seed"], "option_index": index},
    ).json()
    assert result["correct"] is True
    assert result["correct_index"] == index
    assert result["gloss_de"] == lexeme.gloss_de
    assert result["text"]


def test_falsche_antwort_nennt_die_richtige_stelle(client, course):
    api, conn = client
    update_profile(conn, placement_unit=4)
    body = api.get("/api/flashcards/round", params={"direction": "ru_de"}).json()
    karte = body["cards"][0]
    richtig = karte["options_de"].index(course.lexemes[karte["lexeme_id"]].gloss_de)
    falsch = (richtig + 1) % 3

    result = api.post(
        "/api/flashcards/answer",
        json={"lexeme_id": karte["lexeme_id"], "seed": body["seed"], "option_index": falsch},
    ).json()
    assert result["correct"] is False
    assert result["correct_index"] == richtig


def test_die_antwort_wird_vermerkt_und_bringt_das_wort_wieder_nach_vorn(client, course):
    api, conn = client
    update_profile(conn, placement_unit=4)
    body = api.get("/api/flashcards/round", params={"direction": "ru_de"}).json()
    karte = body["cards"][0]
    richtig = karte["options_de"].index(course.lexemes[karte["lexeme_id"]].gloss_de)

    api.post(
        "/api/flashcards/answer",
        json={
            "lexeme_id": karte["lexeme_id"],
            "seed": body["seed"],
            "option_index": (richtig + 1) % 3,
        },
    )
    rows = conn.execute("SELECT lexeme_id, correct FROM flashcard_runs").fetchall()
    assert [(row["lexeme_id"], row["correct"]) for row in rows] == [(karte["lexeme_id"], 0)]

    naechste = api.get("/api/flashcards/round", params={"direction": "ru_de"}).json()
    assert naechste["cards"][0]["lexeme_id"] == karte["lexeme_id"]


def test_die_wiederholung_bleibt_unberuehrt(client, course):
    api, conn = client
    update_profile(conn, placement_unit=4)
    body = api.get("/api/flashcards/round").json()
    karte = body["cards"][0]
    api.post(
        "/api/flashcards/answer",
        json={"lexeme_id": karte["lexeme_id"], "seed": body["seed"], "option_index": 0},
    )
    assert conn.execute("SELECT COUNT(*) FROM lexeme_srs").fetchone()[0] == 0


def test_ein_unbekanntes_wort_ist_ein_404(client):
    api, _ = client
    response = api.post(
        "/api/flashcards/answer",
        json={"lexeme_id": "gibtsnicht", "seed": "s", "option_index": 0},
    )
    assert response.status_code == 404


def test_unbekannte_richtung_wird_abgelehnt(client):
    api, _ = client
    assert api.get("/api/flashcards/round", params={"direction": "x"}).status_code == 422
