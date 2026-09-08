import dataclasses
from pathlib import Path

import pytest

from app.content.loader import load_course
from app.course.presenter import build_sentence_tiles
from app.game import scenes, service
from app.game.loader import load_village
from app.repositories import game_repo, lexeme_srs_repo
from tests.village_factory import write_village

REAL_CONTENT = Path(__file__).resolve().parents[2] / "content" / "ru"


@pytest.fixture
def pair(tmp_path):
    return load_course(REAL_CONTENT), load_village(write_village(tmp_path))


def _correct_submission(course, village, scene_id, seed, index):
    scene = village.scenes[scene_id]
    turn = scenes.scene_turns(course, scene, seed)[index]
    exercise = scenes.turn_exercise(scene, seed, index, turn)
    tiles = build_sentence_tiles(course, exercise)
    return {"tile_indices": [tiles.index(ref) for ref in exercise.solution]}


def test_village_payload_lists_places_with_their_hotspots(pair):
    _, village = pair
    payload = service.village_payload(village)
    bar = next(place for place in payload["places"] if place["id"] == "bar")
    assert bar["name_ru"] == "бар"
    assert bar["hotspot"] == {"x": 0.1, "y": 0.5, "w": 0.2, "h": 0.2}
    assert bar["art"] == "bar"


def test_place_payload_lists_the_people_standing_there(conn, pair):
    course, village = pair
    payload = service.place_payload(village, course, conn, "bar")
    assert [npc["id"] for npc in payload["npcs"]] == ["pjotr"]
    assert payload["kind"] == "npcs"


def test_course_place_points_at_the_first_unfinished_unit(conn, pair):
    course, village = pair
    village.places["bar"] = dataclasses.replace(village.places["bar"], kind="course")
    payload = service.place_payload(village, course, conn, "bar")
    assert payload["next_unit_id"] == 1


def test_start_scene_returns_a_seed_and_the_intro(conn, pair):
    course, village = pair
    started = service.start_scene(
        village, course, conn, place_id="bar", npc_id="pjotr", now="2026-09-08T10:00:00"
    )
    assert started["scene_id"] == "bar-01"
    assert started["turn_count"] == 2
    assert started["intro_de"].startswith("Ein älterer Mann")
    assert started["seed"]


def test_turn_payload_shows_the_npc_line_and_hides_the_solution(pair):
    course, village = pair
    payload = service.turn_payload(course, village, scene_id="bar-01", seed="s1", index=0)
    assert payload["npc_line"]["text"] == "приве́т как дела́"
    assert payload["npc_line"]["audio_text"] == "приве́т как дела́"
    assert payload["exercise"]["type"] == "build_sentence"
    assert "solution" not in payload["exercise"]
    assert len(payload["exercise"]["tiles"]) == 5


def test_turn_payload_names_the_npc_of_the_scene(pair):
    # Eine Szene ist allein durch (scene_id, seed) bestimmt und muss ein
    # Neuladen der Gespraechsansicht ueberstehen; deshalb liefert der Zug
    # selbst mit, mit wem gesprochen wird, statt es dem Router zu ueberlassen.
    course, village = pair
    payload = service.turn_payload(course, village, scene_id="bar-01", seed="s1", index=0)
    assert payload["npc"] == {
        "id": "pjotr",
        "name_ru": "Пётр",
        "name_de": "Pjotr",
        "art": "npc_pjotr",
    }


def test_a_correct_answer_is_graded_and_scheduled(conn, pair):
    course, village = pair
    submission = _correct_submission(course, village, "bar-01", "s1", 0)
    result = service.answer_turn(
        conn, course, village,
        scene_id="bar-01", seed="s1", index=0, submission=submission,
        today="2026-09-08", now="2026-09-08T10:00:00",
    )
    assert result["correct"] is True
    assert result["npc_reaction"] is None
    state = lexeme_srs_repo.get_state(conn, lexeme_id="khorosho", form_key="base")
    assert state is not None


def test_a_wrong_answer_shows_the_solution_and_the_npc_asks_back(conn, pair):
    course, village = pair
    result = service.answer_turn(
        conn, course, village,
        scene_id="bar-01", seed="s1", index=0, submission={"tile_indices": []},
        today="2026-09-08", now="2026-09-08T10:00:00",
    )
    assert result["correct"] is False
    assert result["solution_text"] == "хорошо́ а ты"
    assert result["npc_reaction"]["text"] == "извини́те"


def test_the_last_turn_records_the_run(conn, pair):
    course, village = pair
    submission = _correct_submission(course, village, "bar-01", "s1", 1)
    result = service.answer_turn(
        conn, course, village,
        scene_id="bar-01", seed="s1", index=1, submission=submission,
        today="2026-09-08", now="2026-09-08T10:00:00",
    )
    assert result["scene_completed"] is True
    assert result["outro_de"].startswith("Pjotr nickt")
    assert game_repo.last_played(conn) == {"bar-01": "2026-09-08T10:00:00"}


def test_a_wrong_last_turn_still_ends_the_scene(conn, pair):
    course, village = pair
    result = service.answer_turn(
        conn, course, village,
        scene_id="bar-01", seed="s1", index=1, submission={"tile_indices": []},
        today="2026-09-08", now="2026-09-08T10:00:00",
    )
    assert result["scene_completed"] is True
    assert game_repo.last_played(conn) == {"bar-01": "2026-09-08T10:00:00"}


def test_turn_payload_rejects_a_negative_index(pair):
    course, village = pair
    with pytest.raises(IndexError):
        service.turn_payload(course, village, scene_id="bar-01", seed="s1", index=-1)


def test_answer_turn_rejects_a_negative_index(conn, pair):
    course, village = pair
    with pytest.raises(IndexError):
        service.answer_turn(
            conn, course, village,
            scene_id="bar-01", seed="s1", index=-1, submission={"tile_indices": []},
            today="2026-09-08", now="2026-09-08T10:00:00",
        )


def test_a_shopping_scene_rejects_a_negative_index_too(pair):
    course, village = pair
    with pytest.raises(IndexError):
        service.turn_payload(course, village, scene_id="magazin-01", seed="s1", index=-1)
