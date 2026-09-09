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


def test_reports_scene_with_unknown_npc(tmp_path):
    scene = copy.deepcopy(MINIMAL_DIALOG)
    scene["npc"] = "nirgendwo"
    course, village = _pair(tmp_path, scenes=[scene, MINIMAL_SHOPPING])
    assert any("nirgendwo" in error for error in validate_village(course, village))


def test_reports_turn_with_empty_prompt_de(tmp_path):
    scene = copy.deepcopy(MINIMAL_DIALOG)
    scene["turns"][0]["prompt_de"] = "   "
    course, village = _pair(tmp_path, scenes=[scene, MINIMAL_SHOPPING])
    assert any("prompt_de ist leer" in error for error in validate_village(course, village))


def test_reports_hotspot_outside_zero_to_one(tmp_path):
    places = copy.deepcopy(MINIMAL_PLACES)
    places[0]["hotspot"] = {"x": -0.1, "y": 0.5, "w": 0.2, "h": 0.2}
    course, village = _pair(tmp_path, places=places)
    assert any(
        "außerhalb von 0 bis 1" in error for error in validate_village(course, village)
    )


def test_reports_shopping_scene_without_ask_template(tmp_path):
    scene = copy.deepcopy(MINIMAL_SHOPPING)
    del scene["ask_template"]
    course, village = _pair(tmp_path, scenes=[MINIMAL_DIALOG, scene])
    assert any(
        "shopping braucht ein ask_template" in error
        for error in validate_village(course, village)
    )


def test_reports_ask_template_with_two_item_slots(tmp_path):
    scene = copy.deepcopy(MINIMAL_SHOPPING)
    scene["ask_template"]["solution"].append("{item}")
    course, village = _pair(tmp_path, scenes=[MINIMAL_DIALOG, scene])
    assert any(
        "braucht genau einen" in error for error in validate_village(course, village)
    )


def test_reports_ask_template_prompt_de_without_item_placeholder(tmp_path):
    scene = copy.deepcopy(MINIMAL_SHOPPING)
    scene["ask_template"]["prompt_de"] = "Frag nach der Ware."
    course, village = _pair(tmp_path, scenes=[MINIMAL_DIALOG, scene])
    assert any(
        "enthält kein {item}" in error for error in validate_village(course, village)
    )


def test_reports_a_place_whose_picture_is_missing(tmp_path):
    course, village = _pair(tmp_path)
    empty_art = tmp_path / "leer"
    empty_art.mkdir()
    errors = validate_village(course, village, empty_art)
    assert any("bar" in error and "Datei" in error for error in errors)


def test_accepts_a_place_whose_picture_exists(tmp_path):
    course, village = _pair(tmp_path)
    art_dir = tmp_path / "art"
    art_dir.mkdir()
    for name in ("village", "bar", "magazin", "npc_pjotr", "npc_nina"):
        (art_dir / f"{name}.svg").write_text("<svg/>", encoding="utf-8")
    assert validate_village(course, village, art_dir) == []


def test_reports_npc_at_a_talking_place_without_a_spot(tmp_path):
    npcs = copy.deepcopy(MINIMAL_NPCS)
    del npcs[0]["spot"]
    course, village = _pair(tmp_path, npcs=npcs)
    assert any("Platz im Raum" in error for error in validate_village(course, village))


def test_accepts_a_missing_spot_where_nobody_is_clicked(tmp_path):
    # Nina steht im Laden; der laeuft ueber einen Knopf, nicht ueber Personen.
    course, village = _pair(tmp_path)
    assert validate_village(course, village) == []


def test_reports_spot_reaching_past_the_picture(tmp_path):
    npcs = copy.deepcopy(MINIMAL_NPCS)
    npcs[0]["spot"] = {"x": 0.9, "y": 0.3, "w": 0.3, "h": 0.5}
    course, village = _pair(tmp_path, npcs=npcs)
    assert any("Platz" in error and "hinaus" in error for error in validate_village(course, village))


def test_reports_spot_outside_zero_to_one(tmp_path):
    npcs = copy.deepcopy(MINIMAL_NPCS)
    npcs[0]["spot"] = {"x": -0.1, "y": 0.3, "w": 0.2, "h": 0.5}
    course, village = _pair(tmp_path, npcs=npcs)
    assert any(
        "außerhalb von 0 bis 1" in error for error in validate_village(course, village)
    )


def test_reports_two_people_standing_on_the_same_spot(tmp_path):
    npcs = copy.deepcopy(MINIMAL_NPCS)
    npcs.append(
        {
            "id": "dvojnik",
            "name_ru": "Двойни́к",
            "name_de": "Doppelgänger",
            "place": "bar",
            "about_de": "Steht genau da, wo Pjotr steht.",
            "art": "npc_pjotr",
            "spot": dict(npcs[0]["spot"]),
        }
    )
    course, village = _pair(tmp_path, npcs=npcs)
    assert any("überlappen" in error for error in validate_village(course, village))
