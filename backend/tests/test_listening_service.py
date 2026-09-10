"""Auswahl und Prüfung der Hörgespräche."""

import pytest

from app.content.models import Course, Dialog, DialogLine, DialogSpeaker, Form, Lexeme
from app.course import listening
from app.db import get_connection, init_db
from app.repositories import listening_repo
from app.repositories.profile_repo import get_or_create_profile, update_profile


def _lexeme(lexeme_id: str, text: str, translit: str) -> Lexeme:
    return Lexeme(
        id=lexeme_id,
        lemma=text,
        pos="adv",
        gloss_de=lexeme_id,
        forms={"base": Form(text=text, translit=translit)},
    )


def _dialog(dialog_id: int, min_unit: int) -> Dialog:
    return Dialog(
        id=dialog_id,
        min_unit=min_unit,
        title_de=f"Gespräch {dialog_id}",
        speakers=[
            DialogSpeaker(name_ru="Пётр", name_de="Pjotr", voice="m"),
            DialogSpeaker(name_ru="На́дя", name_de="Nadja", voice="f"),
        ],
        lines=[
            DialogLine(speaker=0, tokens=[("da", "base")], translation_de="Ja."),
            DialogLine(speaker=1, tokens=[("net", "base")], translation_de="Nein."),
            DialogLine(speaker=0, tokens=[("da", "base")], translation_de="Ja."),
        ],
        question_de="Worum ging es?",
        options_de=["Richtig.", "Falsch A.", "Falsch B.", "Falsch C."],
        correct_index=0,
    )


@pytest.fixture
def course() -> Course:
    return Course(
        language="russian",
        lexemes={"da": _lexeme("da", "да", "da"), "net": _lexeme("net", "нет", "net")},
        units={},
        dialogs={1: _dialog(1, min_unit=5), 2: _dialog(2, min_unit=12), 3: _dialog(3, min_unit=40)},
    )


@pytest.fixture
def conn(tmp_path):
    path = str(tmp_path / "test.db")
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


def test_ohne_fortschritt_ist_nichts_freigeschaltet(course, conn):
    assert listening.pick_dialog(course, conn, now="2026-09-10T10:00:00") is None


def test_nur_gespraeche_bis_zur_erreichten_einheit(course, conn):
    _complete(conn, 12)
    freigeschaltet = listening.unlocked(course, listening.reached_unit(conn))
    assert sorted(dialog.id for dialog in freigeschaltet) == [1, 2]


def test_die_einstufung_zaehlt_wie_abgeschlossen(course, conn):
    # Wer bei Einheit 30 einsteigt, hat 1 bis 29 nie angefasst und kann sie doch.
    update_profile(conn, placement_unit=30)
    freigeschaltet = listening.unlocked(course, listening.reached_unit(conn))
    assert sorted(dialog.id for dialog in freigeschaltet) == [1, 2]


def test_nennt_die_einheit_die_das_naechste_gespraech_oeffnet(course, conn):
    assert listening.first_locked_unit(course, listening.reached_unit(conn)) == 5


def test_nimmt_das_am_laengsten_nicht_gehoerte(course, conn):
    _complete(conn, 40)
    listening_repo.record_run(conn, dialog_id=1, correct=True, played_at="2026-09-10T09:00:00")
    listening_repo.record_run(conn, dialog_id=3, correct=True, played_at="2026-09-10T09:30:00")
    dialog, _ = listening.pick_dialog(course, conn, now="2026-09-10T10:00:00")
    # 2 war noch nie dran und geht deshalb vor.
    assert dialog.id == 2


def test_nach_allen_faengt_es_beim_aeltesten_wieder_an(course, conn):
    _complete(conn, 40)
    for dialog_id, moment in ((1, "09:00"), (2, "08:00"), (3, "10:00")):
        listening_repo.record_run(
            conn, dialog_id=dialog_id, correct=True, played_at=f"2026-09-10T{moment}:00"
        )
    dialog, _ = listening.pick_dialog(course, conn, now="2026-09-10T11:00:00")
    assert dialog.id == 2


def test_der_seed_wechselt_mit_der_zeit(course, conn):
    _complete(conn, 40)
    _, erster = listening.pick_dialog(course, conn, now="2026-09-10T10:00:00")
    _, zweiter = listening.pick_dialog(course, conn, now="2026-09-10T11:00:00")
    assert erster != zweiter


def test_payload_verraet_die_loesung_nicht(course):
    payload = listening.dialog_payload(course, course.dialogs[1], seed="s")
    assert "correct_index" not in payload
    assert "title_de" not in payload
    assert all("translation_de" not in line for line in payload["lines"])


def test_payload_traegt_text_und_umschrift_je_zeile(course):
    payload = listening.dialog_payload(course, course.dialogs[1], seed="s")
    assert payload["lines"][0] == {"speaker": 0, "text": "да", "translit": "da"}
    assert [speaker["voice"] for speaker in payload["speakers"]] == ["m", "f"]


def test_optionen_sind_gemischt_aber_vollstaendig(course):
    dialog = course.dialogs[1]
    gemischt = listening.dialog_payload(course, dialog, seed="s")["options_de"]
    assert sorted(gemischt) == sorted(dialog.options_de)


def test_derselbe_seed_mischt_gleich(course):
    dialog = course.dialogs[1]
    erste = listening.dialog_payload(course, dialog, seed="s")["options_de"]
    zweite = listening.dialog_payload(course, dialog, seed="s")["options_de"]
    assert erste == zweite


def test_die_richtige_option_wird_wieder_aufgeloest(course):
    dialog = course.dialogs[1]
    for seed in ("a", "b", "c", "d"):
        gemischt = listening.dialog_payload(course, dialog, seed=seed)["options_de"]
        index = gemischt.index(dialog.options_de[dialog.correct_index])
        assert listening.check_answer(dialog, seed, index) == (True, index)


def test_eine_falsche_wahl_nennt_die_richtige_stelle(course):
    dialog = course.dialogs[1]
    gemischt = listening.dialog_payload(course, dialog, seed="s")["options_de"]
    richtig = gemischt.index(dialog.options_de[dialog.correct_index])
    falsch = (richtig + 1) % len(gemischt)
    assert listening.check_answer(dialog, "s", falsch) == (False, richtig)
