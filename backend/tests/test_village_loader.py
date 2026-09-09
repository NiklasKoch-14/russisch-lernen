import pytest

from app.content.loader import ContentError
from app.game.loader import load_village
from tests.village_factory import write_village


def test_loads_places_keyed_by_id(tmp_path):
    village = load_village(write_village(tmp_path))
    assert village.places["bar"].name_ru == "бар"
    assert village.places["bar"].kind == "npcs"


def test_hotspot_becomes_floats(tmp_path):
    hotspot = load_village(write_village(tmp_path)).places["bar"].hotspot
    assert (hotspot.x, hotspot.y, hotspot.w, hotspot.h) == (0.1, 0.5, 0.2, 0.2)


def test_loads_npcs_with_their_place(tmp_path):
    village = load_village(write_village(tmp_path))
    assert village.npcs["pjotr"].place == "bar"


def test_dialog_turns_become_token_tuples(tmp_path):
    turn = load_village(write_village(tmp_path)).scenes["bar-01"].turns[0]
    assert turn.npc_line == [("privet", "base"), ("kak", "base"), ("dela", "nom.pl")]
    assert turn.solution == [("khorosho", "base"), ("a", "base"), ("ty", "nom")]
    assert turn.distractors == [("plokho", "base"), ("vy", "nom")]


def test_shopping_item_slot_becomes_none(tmp_path):
    scene = load_village(write_village(tmp_path)).scenes["magazin-01"]
    assert scene.ask_template.solution == [
        ("ja", "nom"),
        ("khotet", "prs.1sg"),
        None,
        ("pozhalujsta", "base"),
    ]
    assert scene.pool[0] == ("moloko", "acc.sg")
    assert scene.closing_turn.prompt_de.startswith("Bezahl")


def test_missing_places_file_is_an_error(tmp_path):
    game = write_village(tmp_path)
    (game / "places.json").unlink()
    with pytest.raises(ContentError, match="places.json"):
        load_village(game)


def test_scene_id_must_match_its_filename(tmp_path):
    game = write_village(tmp_path)
    (game / "scenes" / "bar-01.json").rename(game / "scenes" / "anders.json")
    with pytest.raises(ContentError, match="anders.json"):
        load_village(game)
