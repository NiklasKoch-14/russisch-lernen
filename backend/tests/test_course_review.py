import copy

import pytest

from app.content.loader import load_course
from app.course import review
from app.course.review_index import build_index
from app.repositories import lexeme_srs_repo, progress_repo
from app.repositories.lexeme_srs_repo import SrsState
from tests.content_factory import MINIMAL_LEXICON, write_course

TODAY = "2026-09-10"

BUCHSTABEN = [
    {
        "id": "bu_r",
        "lemma": "Р р",
        "pos": "letter",
        "gloss_de": "gerolltes r",
        "forms": {"base": {"text": "Р р", "translit": "r"}},
    },
    {
        "id": "bu_n",
        "lemma": "Н н",
        "pos": "letter",
        "gloss_de": "n wie in nein",
        "forms": {"base": {"text": "Н н", "translit": "n"}},
    },
]


@pytest.fixture
def course(tmp_path):
    lexicon = copy.deepcopy(MINIMAL_LEXICON)
    lexicon["lexemes"].extend(BUCHSTABEN)
    return load_course(write_course(tmp_path, lexicon=lexicon))


@pytest.fixture
def index(course):
    return build_index(course)


@pytest.fixture
def gearbeitet(conn):
    """Einheit 1 wurde angefasst — sonst liefert der Index nichts."""
    progress_repo.bump_progress(conn, unit_id=1, correct=True)
    return conn


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


def _round(conn, course, index):
    return review.build_review_round(conn, course, index, today=TODAY)


def test_leere_runde_wenn_nichts_faellig_ist(conn, course, index):
    assert _round(conn, course, index)["items"] == []


def test_faellige_form_kommt_als_kontext_aufgabe(gearbeitet, course, index):
    _due(gearbeitet, "delat", "prs.1sg")
    items = _round(gearbeitet, course, index)["items"]

    aufgaben = [item for item in items if item["kind"] == "exercise"]
    assert len(aufgaben) == 1
    assert aufgaben[0]["unit_id"] == 1
    assert aufgaben[0]["ref"] == "delat:prs.1sg"
    assert aufgaben[0]["type"] == "choose_form"
    assert "options" in aufgaben[0], "die Aufgabe kommt fertig dargestellt"


def test_formen_ohne_kontext_aufgabe_kommen_als_zuordnung(gearbeitet, course, index):
    _due(gearbeitet, "bu_r", "base")
    _due(gearbeitet, "bu_n", "base")
    items = _round(gearbeitet, course, index)["items"]

    zuordnungen = [item for item in items if item["kind"] == "pairs"]
    assert len(zuordnungen) == 1, "hoechstens eine Zuordnung je Runde"
    assert len(zuordnungen[0]["left"]) == 2


def test_eine_einzelne_form_ohne_kontext_bekommt_gesellschaft(gearbeitet, course, index):
    # Eine Zuordnung mit einem Paar ist keine Aufgabe. Ohne Auffuellen fiele die
    # Form Runde fuer Runde durch und wuerde nie wiederholt.
    _due(gearbeitet, "bu_r", "base")
    _due(gearbeitet, "delat", "prs.1sg")
    items = _round(gearbeitet, course, index)["items"]

    zuordnungen = [item for item in items if item["kind"] == "pairs"]
    assert len(zuordnungen) == 1
    assert len(zuordnungen[0]["left"]) == 2


def test_eine_einzelne_form_ganz_allein_entfaellt(gearbeitet, course, index):
    _due(gearbeitet, "bu_r", "base")
    assert _round(gearbeitet, course, index)["items"] == []


def test_aufgaben_aus_unbearbeiteten_einheiten_kommen_nicht(conn, course, index):
    # kein bump_progress: Einheit 1 wurde nie angefasst
    _due(conn, "delat", "prs.1sg")
    _due(conn, "ja", "nom")
    items = _round(conn, course, index)["items"]
    assert [item for item in items if item["kind"] == "exercise"] == []


def test_formen_ausserhalb_des_lexikons_werden_uebersprungen(gearbeitet, course, index):
    _due(gearbeitet, "gone", "nom")
    _due(gearbeitet, "bu_r", "base")
    _due(gearbeitet, "bu_n", "base")
    items = _round(gearbeitet, course, index)["items"]
    zuordnungen = [item for item in items if item["kind"] == "pairs"]
    assert len(zuordnungen[0]["left"]) == 2


def test_zuordnung_wird_bewertet_und_fortgeschrieben(gearbeitet, course, index):
    _due(gearbeitet, "bu_r", "base")
    _due(gearbeitet, "bu_n", "base")
    items = _round(gearbeitet, course, index)["items"]
    zuordnung = next(item for item in items if item["kind"] == "pairs")

    pairs = []
    for links in zuordnung["left"]:
        gloss = course.gloss(tuple(links["ref"].split(":", 1)))
        rechts = next(r for r in zuordnung["right"] if r["gloss_de"] == gloss)
        pairs.append([links["index"], rechts["index"]])

    ergebnis = review.grade_review_round(
        gearbeitet, course, index, today=TODAY, submission={"pairs": pairs}
    )
    assert ergebnis["correct_count"] == 2
    assert lexeme_srs_repo.get_state(gearbeitet, lexeme_id="bu_r", form_key="base").due_date > TODAY


def test_bewertung_sieht_dieselben_formen_wie_die_runde(gearbeitet, course, index):
    # Die Runde zweigt Formen mit Kontext-Aufgabe ab. Wuerde die Bewertung
    # wieder von allen faelligen Formen ausgehen, benotete sie andere.
    _due(gearbeitet, "bu_r", "base")
    _due(gearbeitet, "bu_n", "base")
    _due(gearbeitet, "delat", "prs.1sg")

    zuordnung = next(
        item for item in _round(gearbeitet, course, index)["items"] if item["kind"] == "pairs"
    )
    ergebnis = review.grade_review_round(
        gearbeitet, course, index, today=TODAY, submission={"pairs": []}
    )
    assert ergebnis["total_count"] == len(zuordnung["left"])
