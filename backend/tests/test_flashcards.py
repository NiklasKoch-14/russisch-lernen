"""Karteikarten: Stapel bauen, Ablenker ziehen, Antwort prüfen."""

import pytest

from app.content.models import Course, Form, Lexeme, Unit
from app.course import flashcards
from app.db import get_connection, init_db
from app.repositories import flashcard_repo
from app.repositories.profile_repo import get_or_create_profile


def _lexeme(lexeme_id: str, text: str, gloss: str, pos: str = "noun") -> Lexeme:
    key = "base" if pos not in ("noun", "verb") else ("nom.sg" if pos == "noun" else "inf")
    return Lexeme(
        id=lexeme_id,
        lemma=text,
        pos=pos,
        gloss_de=gloss,
        forms={key: Form(text=text, translit=lexeme_id)},
    )


def _unit(unit_id: int, lexeme_ids: list[str]) -> Unit:
    from app.content.models import GrammarFocus

    return Unit(
        id=unit_id,
        stage=1,
        title_de=f"Einheit {unit_id}",
        scenario_de="",
        grammar_focus=GrammarFocus(id="f", title_de="t", explanation_de="e"),
        new_lexemes=lexeme_ids,
        exercises=[],
    )


NOMEN = {
    "khleb": ("хлеб", "das Brot"),
    "syr": ("сыр", "der Käse"),
    "butylka": ("буты́лка", "die Flasche"),
    "chashka": ("ча́шка", "die Tasse"),
    "paket": ("паке́т", "die Tüte"),
    "kniga": ("кни́га", "das Buch"),
}
VERBEN = {
    "pit": ("пить", "trinken"),
    "govorit": ("говори́ть", "sprechen"),
    "chitat": ("чита́ть", "lesen"),
}


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
        4: _unit(4, ["chitat"]),
    }
    return Course(language="russian", lexemes=lexemes, units=units)


@pytest.fixture
def conn(tmp_path):
    path = str(tmp_path / "karten.db")
    init_db(path)
    connection = get_connection(path)
    get_or_create_profile(connection, "russian")
    yield connection
    connection.close()


def _complete(conn, unit_id: int) -> None:
    conn.execute(
        "INSERT INTO unit_progress (unit_id, status, correct_count, total_count, completed_at)"
        " VALUES (?, 'completed', 1, 1, '2026-09-10T09:00:00')",
        (unit_id,),
    )
    conn.commit()


# --- welche Wörter im Stapel liegen ------------------------------------------


def test_nur_woerter_bis_zur_erreichten_einheit(course):
    ids = {lexeme.id for lexeme in flashcards.known_lexemes(course, 2)}
    assert ids == {"khleb", "syr", "butylka", "chashka"}


def test_buchstaben_sind_keine_vokabeln(course):
    ids = {lexeme.id for lexeme in flashcards.known_lexemes(course, 4)}
    assert "bu_r" not in ids


def test_ohne_fortschritt_ist_der_stapel_leer(course, conn):
    assert flashcards.build_round(course, conn, direction="mixed", seed="s") == []


# --- Reihenfolge --------------------------------------------------------------


def test_zuletzt_falsche_kommen_zuerst(course, conn):
    _complete(conn, 3)
    for lexeme_id in ("khleb", "syr", "butylka", "chashka", "paket", "kniga"):
        flashcard_repo.record(
            conn, lexeme_id=lexeme_id, correct=True, answered_at="2026-09-10T09:00:00"
        )
    flashcard_repo.record(conn, lexeme_id="kniga", correct=False, answered_at="2026-09-10T09:30:00")

    karten = flashcards.build_round(course, conn, direction="ru_de", seed="s", count=3)
    assert karten[0]["lexeme_id"] == "kniga"


def test_nie_gesehene_kommen_vor_den_richtig_beantworteten(course, conn):
    _complete(conn, 3)
    for lexeme_id in ("khleb", "syr", "butylka", "chashka"):
        flashcard_repo.record(
            conn, lexeme_id=lexeme_id, correct=True, answered_at="2026-09-10T09:00:00"
        )

    karten = flashcards.build_round(course, conn, direction="ru_de", seed="s", count=4)
    gezogen = {karte["lexeme_id"] for karte in karten}
    assert {"paket", "kniga", "pit", "govorit"} == gezogen


def test_die_runde_ist_nicht_laenger_als_verlangt(course, conn):
    _complete(conn, 4)
    assert len(flashcards.build_round(course, conn, direction="ru_de", seed="s", count=5)) == 5


# --- die Karte selbst ---------------------------------------------------------


def test_russisch_nach_deutsch_zeigt_das_wort_und_drei_bedeutungen(course, conn):
    _complete(conn, 3)
    karte = flashcards.build_round(course, conn, direction="ru_de", seed="s", count=1)[0]
    assert karte["direction"] == "ru_de"
    assert karte["prompt_ru"]["text"]
    assert karte["prompt_de"] is None
    assert len(karte["options_de"]) == 3
    assert karte["options_ru"] == []


def test_deutsch_nach_russisch_dreht_die_karte_um(course, conn):
    _complete(conn, 3)
    karte = flashcards.build_round(course, conn, direction="de_ru", seed="s", count=1)[0]
    assert karte["direction"] == "de_ru"
    assert karte["prompt_de"]
    assert karte["prompt_ru"] is None
    assert len(karte["options_ru"]) == 3
    assert all("translit" in option for option in karte["options_ru"])


def test_gemischt_bringt_beide_richtungen(course, conn):
    _complete(conn, 4)
    karten = flashcards.build_round(course, conn, direction="mixed", seed="s", count=9)
    assert {karte["direction"] for karte in karten} == {"ru_de", "de_ru"}


def test_die_loesung_steht_nicht_in_der_karte(course, conn):
    _complete(conn, 3)
    karte = flashcards.build_round(course, conn, direction="ru_de", seed="s", count=1)[0]
    assert "correct_index" not in karte
    assert "gloss_de" not in karte


def test_ablenker_kommen_aus_derselben_wortart(course, conn):
    # „die Flasche" gegen „sprechen" waere keine Frage.
    _complete(conn, 4)
    karten = flashcards.build_round(course, conn, direction="ru_de", seed="s", count=9)
    for karte in karten:
        wortart = course.lexemes[karte["lexeme_id"]].pos
        gleiche = [
            lexeme.gloss_de
            for lexeme in course.lexemes.values()
            if lexeme.pos == wortart and lexeme.pos != "letter"
        ]
        assert all(option in gleiche for option in karte["options_de"]), karte


def test_keine_option_kommt_doppelt_vor(course, conn):
    _complete(conn, 4)
    for karte in flashcards.build_round(course, conn, direction="mixed", seed="s", count=9):
        optionen = karte["options_de"] or [option["text"] for option in karte["options_ru"]]
        assert len(set(optionen)) == 3


# --- prüfen -------------------------------------------------------------------


def test_die_richtige_option_wird_erkannt(course, conn):
    _complete(conn, 3)
    for karte in flashcards.build_round(course, conn, direction="mixed", seed="s", count=6):
        lexeme = course.lexemes[karte["lexeme_id"]]
        gesucht = (
            lexeme.gloss_de
            if karte["direction"] == "ru_de"
            else next(iter(lexeme.forms.values())).text
        )
        optionen = karte["options_de"] or [option["text"] for option in karte["options_ru"]]
        index = optionen.index(gesucht)
        richtig, correct_index = flashcards.check_answer(
            course, conn, karte["lexeme_id"], seed="s", option_index=index
        )
        assert richtig and correct_index == index


def test_eine_falsche_wahl_nennt_die_richtige_stelle(course, conn):
    _complete(conn, 3)
    karte = flashcards.build_round(course, conn, direction="ru_de", seed="s", count=1)[0]
    lexeme = course.lexemes[karte["lexeme_id"]]
    richtig = karte["options_de"].index(lexeme.gloss_de)
    falsch = (richtig + 1) % 3
    assert flashcards.check_answer(
        course, conn, karte["lexeme_id"], seed="s", option_index=falsch
    ) == (False, richtig)


def test_geprueft_wird_gegen_denselben_stapel_wie_gezeigt(course, conn):
    # Der Ablenker-Zug haengt am Stapel. Wuerde beim Pruefen aus dem ganzen Kurs
    # gezogen und beim Zeigen nur aus den gelernten Woertern, zeigte die Antwort
    # auf eine andere Option als die angeklickte.
    _complete(conn, 2)
    for karte in flashcards.build_round(course, conn, direction="ru_de", seed="s", count=4):
        lexeme = course.lexemes[karte["lexeme_id"]]
        index = karte["options_de"].index(lexeme.gloss_de)
        assert flashcards.check_answer(
            course, conn, karte["lexeme_id"], seed="s", option_index=index
        ) == (True, index)
