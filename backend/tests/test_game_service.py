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


def test_place_payload_says_where_each_person_stands(conn, pair):
    course, village = pair
    payload = service.place_payload(village, course, conn, "bar")
    assert payload["npcs"][0]["spot"] == {"x": 0.1, "y": 0.3, "w": 0.15, "h": 0.5}


def test_place_payload_reports_a_missing_spot_as_null(conn, pair):
    # Im Laden wird niemand angeklickt; die Ansicht muss das unterscheiden koennen.
    course, village = pair
    payload = service.place_payload(village, course, conn, "magazin")
    assert payload["npcs"][0]["spot"] is None


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


def _typed_submission(course, village, scene_id, seed, index):
    scene = village.scenes[scene_id]
    turn = scenes.scene_turns(course, scene, seed)[index]
    return {"text": " ".join(course.form(ref).text for ref in turn.solution)}


class TestTippenImDorf:
    def test_turn_payload_asks_for_a_typed_sentence(self, pair):
        course, village = pair
        payload = service.turn_payload(
            course, village, scene_id="bar-01", seed="s1", index=0, typed=True
        )
        assert payload["exercise"]["type"] == "type_sentence"
        assert payload["exercise"]["word_count"] == 3
        assert "tiles" not in payload["exercise"]

    def test_turn_payload_still_shows_the_npc_line_when_typing(self, pair):
        course, village = pair
        payload = service.turn_payload(
            course, village, scene_id="bar-01", seed="s1", index=0, typed=True
        )
        assert payload["npc_line"]["text"] == "приве́т как дела́"

    def test_turn_payload_keeps_tiles_by_default(self, pair):
        course, village = pair
        payload = service.turn_payload(course, village, scene_id="bar-01", seed="s1", index=0)
        assert payload["exercise"]["type"] == "build_sentence"

    def test_a_typed_answer_is_graded(self, conn, pair):
        course, village = pair
        result = service.answer_turn(
            conn, course, village,
            scene_id="bar-01", seed="s1", index=0,
            submission=_typed_submission(course, village, "bar-01", "s1", 0),
            today="2026-09-09", now="2026-09-09T12:00:00",
        )
        assert result["correct"] is True

    def test_a_wrong_typed_answer_gets_the_diagnosis(self, conn, pair):
        course, village = pair
        result = service.answer_turn(
            conn, course, village,
            scene_id="bar-01", seed="s1", index=0,
            submission={"text": "пло́хо а ты"},
            today="2026-09-09", now="2026-09-09T12:00:00",
        )
        assert result["correct"] is False
        assert "хорошо́" in result["explanation_de"]
        assert result["npc_reaction"] is not None

    def test_the_submission_decides_how_it_is_graded(self, conn, pair):
        # Der Schalter darf mitten im Zug umgelegt werden koennen, ohne dass
        # die Pruefung nicht mehr zu dem passt, was auf dem Schirm stand.
        course, village = pair
        result = service.answer_turn(
            conn, course, village,
            scene_id="bar-01", seed="s1", index=0,
            submission=_correct_submission(course, village, "bar-01", "s1", 0),
            today="2026-09-09", now="2026-09-09T12:00:00",
        )
        assert result["correct"] is True
