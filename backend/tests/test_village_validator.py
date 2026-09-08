import copy
from pathlib import Path

from app.content.loader import load_course
from app.game.loader import load_village
from app.game.validator import validate_village
from tests.content_factory import write_course
from tests.village_factory import (
    MINIMAL_DIALOG,
    MINIMAL_NPCS,
    MINIMAL_PLACES,
    MINIMAL_SHOPPING,
    write_village,
)

REAL_CONTENT = Path(__file__).resolve().parents[2] / "content" / "ru"


def _pair(tmp_path, *, places=None, npcs=None, scenes=None):
    """Echtes Lexikon, damit die Token der Beispielszenen auflösbar sind."""
    course = load_course(REAL_CONTENT)
    village = load_village(write_village(tmp_path, places=places, npcs=npcs, scenes=scenes))
    return course, village


def test_valid_village_has_no_errors(tmp_path):
    course, village = _pair(tmp_path)
    assert validate_village(course, village) == []


def test_reports_unknown_lexeme_in_a_turn(tmp_path):
    scene = copy.deepcopy(MINIMAL_DIALOG)
    scene["turns"][0]["solution"] = [["gibtsnicht", "base"]]
    course, village = _pair(tmp_path, scenes=[scene, MINIMAL_SHOPPING])
    assert any("gibtsnicht" in error for error in validate_village(course, village))


def test_reports_form_missing_from_the_lexeme(tmp_path):
    scene = copy.deepcopy(MINIMAL_DIALOG)
    scene["turns"][0]["solution"] = [["ty", "ins"]]
    course, village = _pair(tmp_path, scenes=[scene, MINIMAL_SHOPPING])
    assert any("ins" in error for error in validate_village(course, village))


def test_reports_scene_at_unknown_place(tmp_path):
    scene = copy.deepcopy(MINIMAL_DIALOG)
    scene["place"] = "nirgendwo"
    course, village = _pair(tmp_path, scenes=[scene, MINIMAL_SHOPPING])
    assert any("nirgendwo" in error for error in validate_village(course, village))


def test_reports_npc_at_unknown_place(tmp_path):
    npcs = copy.deepcopy(MINIMAL_NPCS)
    npcs[0]["place"] = "nirgendwo"
    course, village = _pair(tmp_path, npcs=npcs)
    assert any("nirgendwo" in error for error in validate_village(course, village))


def test_reports_distractor_that_is_part_of_the_solution(tmp_path):
    scene = copy.deepcopy(MINIMAL_DIALOG)
    scene["turns"][0]["distractors"] = [["ty", "nom"]]
    course, village = _pair(tmp_path, scenes=[scene, MINIMAL_SHOPPING])
    assert any("Ablenker" in error for error in validate_village(course, village))


def test_reports_scene_with_a_single_turn(tmp_path):
    scene = copy.deepcopy(MINIMAL_DIALOG)
    scene["turns"] = scene["turns"][:1]
    course, village = _pair(tmp_path, scenes=[scene, MINIMAL_SHOPPING])
    assert any("zwei Züge" in error for error in validate_village(course, village))


def test_reports_hotspot_reaching_past_the_map(tmp_path):
    places = copy.deepcopy(MINIMAL_PLACES)
    places[0]["hotspot"] = {"x": 0.9, "y": 0.5, "w": 0.3, "h": 0.2}
    course, village = _pair(tmp_path, places=places)
    assert any("Klickfläche" in error for error in validate_village(course, village))


def test_reports_overlapping_hotspots(tmp_path):
    places = copy.deepcopy(MINIMAL_PLACES)
    places[1]["hotspot"] = dict(places[0]["hotspot"])
    course, village = _pair(tmp_path, places=places)
    assert any("überlappen" in error for error in validate_village(course, village))


def test_reports_shopping_pool_that_is_too_small(tmp_path):
    scene = copy.deepcopy(MINIMAL_SHOPPING)
    scene["count"] = len(scene["pool"])
    course, village = _pair(tmp_path, scenes=[MINIMAL_DIALOG, scene])
    assert any("Pool" in error for error in validate_village(course, village))


def test_reports_hint_unit_that_does_not_exist(tmp_path):
    scene = copy.deepcopy(MINIMAL_DIALOG)
    scene["hint_unit"] = 999
    course, village = _pair(tmp_path, scenes=[scene, MINIMAL_SHOPPING])
    assert any("999" in error for error in validate_village(course, village))
