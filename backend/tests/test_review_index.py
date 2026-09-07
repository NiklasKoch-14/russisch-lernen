import copy

from app.content.loader import load_course
from app.course.review_index import build_index
from tests.content_factory import MINIMAL_UNIT, write_course


def _course(tmp_path, units=None):
    return load_course(write_course(tmp_path, units=units))


def test_choose_form_landet_unter_genau(tmp_path):
    index = build_index(_course(tmp_path))
    assert (1, "1-2") in index.exact[("delat", "prs.1sg")]


def test_build_sentence_landet_unter_weit(tmp_path):
    index = build_index(_course(tmp_path))
    assert (1, "1-1") in index.broad[("ja", "nom")]


def test_pick_bevorzugt_die_genaue_aufgabe(tmp_path):
    index = build_index(_course(tmp_path))
    assert index.pick(("delat", "prs.1sg"), allowed_units={1}, seed="x") == (1, "1-2")


def test_pick_nimmt_weit_wenn_es_nichts_genaues_gibt(tmp_path):
    index = build_index(_course(tmp_path))
    assert index.pick(("ja", "nom"), allowed_units={1}, seed="x") == (1, "1-1")


def test_pick_meidet_einheiten_ohne_fortschritt(tmp_path):
    index = build_index(_course(tmp_path))
    assert index.pick(("delat", "prs.1sg"), allowed_units=set(), seed="x") is None


def test_pick_liefert_none_fuer_unbekannte_form(tmp_path):
    index = build_index(_course(tmp_path))
    assert index.pick(("gibtesnicht", "nom"), allowed_units={1}, seed="x") is None


def test_pick_streut_ueber_mehrere_kandidaten(tmp_path):
    # Zwei choose_form-Aufgaben auf dieselbe Form: die Wahl darf nicht immer
    # auf dieselbe fallen, sonst sieht man ewig denselben Satz.
    unit = copy.deepcopy(MINIMAL_UNIT)
    zweite = copy.deepcopy(unit["exercises"][1])
    zweite["id"] = "1-9"
    unit["exercises"] = unit["exercises"] + [zweite]
    index = build_index(_course(tmp_path, units=[unit]))

    gewaehlt = {
        index.pick(("delat", "prs.1sg"), allowed_units={1}, seed=f"tag-{tag}")
        for tag in range(12)
    }
    assert len(gewaehlt) == 2


def test_pick_ist_innerhalb_eines_tages_stabil(tmp_path):
    index = build_index(_course(tmp_path))
    a = index.pick(("delat", "prs.1sg"), allowed_units={1}, seed="2026-09-07")
    b = index.pick(("delat", "prs.1sg"), allowed_units={1}, seed="2026-09-07")
    assert a == b
