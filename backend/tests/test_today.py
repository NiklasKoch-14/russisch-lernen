"""Der Tagesplan der Startseite — je Regel aus der Spec ein Test."""

import pytest

from app.content.models import (
    Course,
    Dialog,
    DialogLine,
    DialogSpeaker,
    Form,
    GrammarFocus,
    Lexeme,
    MatchPairsExercise,
    Unit,
)
from app.course import today as today_module
from app.course.review_index import build_index
from app.game.models import Hotspot, Place, Scene, Village
from app.repositories import game_repo, lexeme_srs_repo, listening_repo, progress_repo, review_repo
from app.repositories.lexeme_srs_repo import SrsState
from app.repositories.profile_repo import get_or_create_profile, update_profile

TODAY = "2026-09-11"  # ein Freitag
YESTERDAY = "2026-09-10"
LONG_AGO = "2026-09-01"


def _unit(unit_id: int) -> Unit:
    return Unit(
        id=unit_id,
        stage=1,
        title_de=f"Einheit {unit_id}",
        scenario_de=f"Szenario {unit_id}",
        grammar_focus=GrammarFocus(id="g", title_de="Regel", explanation_de="Text"),
        new_lexemes=["da", "net"],
        exercises=[
            MatchPairsExercise(id=f"{unit_id}-{n}", prompt_de="Ordne zu.", pairs=[])
            for n in range(3)
        ],
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
        lines=[DialogLine(speaker=0, tokens=[("da", "base")], translation_de="Ja.")],
        question_de="Worum ging es?",
        options_de=["A", "B", "C", "D"],
        correct_index=0,
    )


def _scene(scene_id: str, place: str, hint_unit: int) -> Scene:
    return Scene(
        id=scene_id, kind="dialog", place=place, npc="lena",
        title_de=f"Szene {scene_id}", hint_unit=hint_unit,
    )


@pytest.fixture
def course() -> Course:
    lexemes = {
        lexeme_id: Lexeme(
            id=lexeme_id, lemma=text, pos="adv", gloss_de=lexeme_id,
            forms={"base": Form(text=text, translit=lexeme_id)},
        )
        for lexeme_id, text in (
            ("da", "да"),
            ("net", "нет"),
            # Genug Wörter, um einen Rückstand fällig zu stellen.
            *((f"f{number}", "да") for number in range(50)),
        )
    }
    return Course(
        language="russian",
        lexemes=lexemes,
        units={unit_id: _unit(unit_id) for unit_id in range(1, 6)},
        dialogs={1: _dialog(1, min_unit=2), 2: _dialog(2, min_unit=4)},
    )


@pytest.fixture
def village() -> Village:
    spot = Hotspot(x=0, y=0, w=0.1, h=0.1)
    return Village(
        places={
            "kafe": Place(id="kafe", name_ru="Кафе́", name_de="Café", kind="npcs", art="kafe",
                          hotspot=spot),
        },
        npcs={},
        scenes={"kafe-01": _scene("kafe-01", "kafe", hint_unit=3)},
    )


@pytest.fixture
def db(conn):
    get_or_create_profile(conn, "russian")
    return conn


def _plan(db, course, village):
    return today_module.build_plan(db, course, village, build_index(course), today=TODAY)


def _step(plan, kind):
    return next((step for step in plan["steps"] if step["kind"] == kind), None)


def _complete(conn, unit_id, day):
    conn.execute(
        "INSERT INTO unit_progress (unit_id, status, correct_count, total_count, completed_at)"
        " VALUES (?, 'completed', 0, 0, ?)",
        (unit_id, f"{day}T10:00:00+00:00"),
    )
    conn.commit()


def _practised(conn, day):
    """Irgendeine Aktivität an diesem Tag — hier eine Aufgabe in Einheit 1."""
    conn.execute(
        "INSERT INTO exercise_attempts (unit_id, exercise_id, correct, answer_json, created_at)"
        " VALUES (1, '1-0', 1, '{}', ?)",
        (f"{day}T10:00:00+00:00",),
    )
    conn.commit()


def _due(conn, count, prefix="f"):
    for number in range(count):
        lexeme_srs_repo.upsert_state(
            conn,
            SrsState(lexeme_id=f"{prefix}{number}", form_key="base", interval_days=1.0,
                     ease_factor=2.5, repetitions=1, due_date=LONG_AGO),
        )


def _reviewed(conn, count, day=TODAY):
    for number in range(count):
        review_repo.record_run(conn, lexeme_id=f"r{number}", form_key="base", correct=True,
                               answered_at=day)


# --- erster Tag -----------------------------------------------------------


def test_am_ersten_tag_steht_nur_die_erste_einheit_an(db, course, village):
    plan = _plan(db, course, village)
    assert [step["kind"] for step in plan["steps"]] == ["unit"]
    unit = plan["steps"][0]
    assert (unit["unit_id"], unit["status"], unit["link"]) == (1, "next", "/kurs/1")
    assert unit["title_de"] == "Einheit 1"
    assert unit["detail_de"] == "Szenario 1"
    assert unit["minutes"] == 4  # drei Aufgaben und zwei neue Wörter
    assert plan["offer_screening"] is True
    assert plan["greeting"] == "normal"
    assert plan["finished"] is False
    assert plan["week_days"] == 0


def test_die_einstufung_setzt_den_anfang(db, course, village):
    update_profile(db, placement_unit=3)
    plan = _plan(db, course, village)
    assert _step(plan, "unit")["unit_id"] == 3
    assert plan["offer_screening"] is False


# --- Auffrischen ----------------------------------------------------------


def test_faelliges_kommt_zuerst(db, course, village):
    _due(db, 3)
    plan = _plan(db, course, village)
    assert [step["kind"] for step in plan["steps"]] == ["review", "unit"]
    review = plan["steps"][0]
    assert (review["status"], review["link"], review["minutes"]) == ("next", "/wiederholen", 2)
    assert plan["steps"][1]["status"] == "later"


def test_auffrischen_ist_erledigt_wenn_nichts_mehr_faellig_ist(db, course, village):
    _reviewed(db, 3)
    plan = _plan(db, course, village)
    assert _step(plan, "review")["status"] == "done"
    assert _step(plan, "unit")["status"] == "next"


def test_nach_zwanzig_formen_ist_fuer_heute_schluss(db, course, village):
    _due(db, 10)
    _reviewed(db, 20)
    assert _step(_plan(db, course, village), "review")["status"] == "done"


def test_eine_einzelne_form_ohne_aufgabe_fuehrt_nicht_ins_leere(db, course, village):
    # Eine einzelne Form ohne Kursaufgabe ergibt keine Zuordnung — die
    # Wiederholung zeigt dann nichts. Die Startseite darf nicht dorthin schicken.
    _due(db, 1)
    assert _step(_plan(db, course, village), "review") is None


def test_ist_nichts_mehr_zu_zeigen_gilt_das_auffrischen_als_erledigt(db, course, village):
    _due(db, 1)
    _reviewed(db, 3)
    assert _step(_plan(db, course, village), "review")["status"] == "done"


def test_gestern_geuebtes_zaehlt_nicht_fuer_heute(db, course, village):
    _due(db, 5)
    _reviewed(db, 20, day=YESTERDAY)
    assert _step(_plan(db, course, village), "review")["status"] == "next"


# --- neue Einheit ---------------------------------------------------------


def test_angefangene_einheit_geht_vor(db, course, village):
    _complete(db, 1, LONG_AGO)
    progress_repo.bump_progress(db, unit_id=3, correct=True)
    assert _step(_plan(db, course, village), "unit")["unit_id"] == 3


def test_heute_abgeschlossene_einheit_bleibt_mit_haken_stehen(db, course, village):
    _complete(db, 1, TODAY)
    plan = _plan(db, course, village)
    unit = _step(plan, "unit")
    assert (unit["unit_id"], unit["status"]) == (1, "done")
    assert plan["next_unit_id"] == 2


def test_nach_langer_pause_keine_neue_einheit(db, course, village):
    _complete(db, 1, LONG_AGO)
    _practised(db, LONG_AGO)
    plan = _plan(db, course, village)
    assert _step(plan, "unit") is None
    assert plan["unit_skipped"] == "pause"
    assert plan["greeting"] == "welcome_back"
    assert plan["next_unit_id"] == 2


def test_am_zweiten_tag_nach_der_pause_geht_es_normal_weiter(db, course, village):
    _complete(db, 1, LONG_AGO)
    _practised(db, LONG_AGO)
    _practised(db, YESTERDAY)
    plan = _plan(db, course, village)
    assert plan["greeting"] == "normal"
    assert _step(plan, "unit")["unit_id"] == 2


def test_die_pause_gilt_den_ganzen_ersten_tag(db, course, village):
    # Wer heute schon etwas getan hat, ist trotzdem erst heute zurück.
    _practised(db, LONG_AGO)
    _practised(db, TODAY)
    assert _plan(db, course, village)["greeting"] == "welcome_back"


def test_bei_hohem_rueckstand_keine_neue_einheit(db, course, village):
    _due(db, 41)
    plan = _plan(db, course, village)
    assert _step(plan, "unit") is None
    assert plan["unit_skipped"] == "backlog"


def test_der_rueckstand_zaehlt_das_heute_abgearbeitete_mit(db, course, village):
    # Sonst tauchte die Einheit mitten am Tag auf, sobald ein paar Formen weg sind.
    _due(db, 25)
    _reviewed(db, 20)
    assert _plan(db, course, village)["unit_skipped"] == "backlog"


def test_eine_heute_trotzdem_gemachte_einheit_steht_im_plan(db, course, village):
    _due(db, 41)
    _complete(db, 1, TODAY)
    assert _step(_plan(db, course, village), "unit")["status"] == "done"


def test_wenn_alles_geschafft_ist(db, course, village):
    for unit_id in range(1, 6):
        _complete(db, unit_id, LONG_AGO)
    plan = _plan(db, course, village)
    assert _step(plan, "unit") is None
    assert plan["unit_skipped"] == "all_done"
    assert plan["next_unit_id"] is None


# --- Anwenden -------------------------------------------------------------


def _reached_four(db):
    for unit_id in range(1, 5):
        _complete(db, unit_id, LONG_AGO)
    _practised(db, YESTERDAY)


def test_neues_gespraech_nah_an_der_letzten_einheit(db, course, village):
    _reached_four(db)
    apply = _step(_plan(db, course, village), "listening")
    assert apply["link"] == "/hoeren?gespraech=2"
    assert apply["title_de"] == "Gespräch 2"
    assert apply["known"] is False
    assert apply["minutes"] == 3


def test_danach_die_naechste_unbekannte_szene(db, course, village):
    _reached_four(db)
    listening_repo.record_run(db, dialog_id=2, correct=True, played_at=f"{YESTERDAY}T09:00:00")
    apply = _step(_plan(db, course, village), "scene")
    assert apply["link"] == "/dorf/kafe?szene=kafe-01"
    assert apply["title_de"] == "Szene kafe-01"
    assert apply["detail_de"] == "Café"
    assert apply["minutes"] == 4


def test_heute_gespieltes_ist_erledigt(db, course, village):
    _reached_four(db)
    game_repo.record_run(db, scene_id="kafe-01", seed="s", played_at=f"{TODAY}T09:00:00")
    apply = _step(_plan(db, course, village), "scene")
    assert (apply["title_de"], apply["status"]) == ("Szene kafe-01", "done")


def test_nach_der_pause_kommt_etwas_bekanntes(db, course, village):
    for unit_id in range(1, 5):
        _complete(db, unit_id, LONG_AGO)
    listening_repo.record_run(db, dialog_id=1, correct=True, played_at=f"{LONG_AGO}T09:00:00")
    apply = _step(_plan(db, course, village), "listening")
    assert apply["link"] == "/hoeren?gespraech=1"
    assert apply["known"] is True


def test_ohne_freigeschaltetes_kein_anwenden(db, course, village):
    plan = _plan(db, course, village)
    assert _step(plan, "listening") is None
    assert _step(plan, "scene") is None


# --- Ende und Woche -------------------------------------------------------


def test_fertig_wenn_alle_schritte_erledigt_sind(db, course, village):
    _reached_four(db)
    _reviewed(db, 3)
    _complete(db, 5, TODAY)
    listening_repo.record_run(db, dialog_id=2, correct=True, played_at=f"{TODAY}T11:00:00")
    plan = _plan(db, course, village)
    assert [step["status"] for step in plan["steps"]] == ["done", "done", "done"]
    assert plan["finished"] is True


def test_die_woche_zaehlt_uebungstage_seit_montag(db, course, village):
    _practised(db, "2026-09-06")  # Sonntag davor
    _practised(db, "2026-09-07")  # Montag
    review_repo.record_run(db, lexeme_id="x", form_key="base", correct=True,
                           answered_at="2026-09-09")
    assert _plan(db, course, village)["week_days"] == 2
