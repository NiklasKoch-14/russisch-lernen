from pathlib import Path

from app.content.loader import load_course
from app.game import scenes
from app.game.loader import load_village
from app.repositories import game_repo
from tests.village_factory import MINIMAL_DIALOG, write_village

REAL_CONTENT = Path(__file__).resolve().parents[2] / "content" / "ru"


def _pair(tmp_path):
    return load_course(REAL_CONTENT), load_village(write_village(tmp_path))


def _dialog_scene(scene_id: str, *, place: str = "bar", npc: str = "pjotr") -> dict:
    """Klon von MINIMAL_DIALOG unter anderer Id — für Tests mit mehreren Szenen am selben Ort."""
    scene = dict(MINIMAL_DIALOG)
    scene["id"] = scene_id
    scene["place"] = place
    scene["npc"] = npc
    return scene


def test_dialog_turns_are_taken_as_written(tmp_path):
    course, village = _pair(tmp_path)
    turns = scenes.scene_turns(course, village.scenes["bar-01"], seed="egal")
    assert [turn.prompt_de for turn in turns] == [
        "Sag, dass es dir gut geht, und frag zurück.",
        "Verabschiede dich locker.",
    ]


def test_shopping_builds_one_turn_per_item_plus_the_closing_turn(tmp_path):
    course, village = _pair(tmp_path)
    turns = scenes.scene_turns(course, village.scenes["magazin-01"], seed="s1")
    assert len(turns) == village.scenes["magazin-01"].count + 1
    assert turns[-1].prompt_de.startswith("Bezahl")


def test_the_same_seed_yields_the_same_shopping_list(tmp_path):
    course, village = _pair(tmp_path)
    scene = village.scenes["magazin-01"]
    first = [turn.solution for turn in scenes.scene_turns(course, scene, seed="s1")]
    second = [turn.solution for turn in scenes.scene_turns(course, scene, seed="s1")]
    assert first == second


def test_a_different_seed_yields_a_different_list(tmp_path):
    course, village = _pair(tmp_path)
    scene = village.scenes["magazin-01"]
    lists = {
        tuple(str(turn.solution) for turn in scenes.scene_turns(course, scene, seed=seed))
        for seed in ("s1", "s2", "s3", "s4", "s5")
    }
    assert len(lists) > 1


def test_the_item_lands_in_the_solution_and_in_the_prompt(tmp_path):
    course, village = _pair(tmp_path)
    turn = scenes.scene_turns(course, village.scenes["magazin-01"], seed="s1")[0]
    assert None not in turn.solution
    item = turn.solution[2]
    assert course.gloss(item) in turn.prompt_de


def test_shopping_distractors_come_from_the_unused_pool(tmp_path):
    course, village = _pair(tmp_path)
    scene = village.scenes["magazin-01"]
    turns = scenes.scene_turns(course, scene, seed="s1")
    chosen = {turn.solution[2] for turn in turns[:-1]}
    for turn in turns[:-1]:
        assert set(turn.distractors).isdisjoint(chosen)
        assert set(turn.distractors) <= set(scene.pool)


def test_shopping_distractors_differ_between_turns_of_the_same_round(tmp_path):
    course, village = _pair(tmp_path)
    scene = village.scenes["magazin-01"]
    turns = scenes.scene_turns(course, scene, seed="s1")
    distractor_sets = {tuple(turn.distractors) for turn in turns[:-1]}
    assert len(distractor_sets) > 1


def test_turn_becomes_a_build_sentence_exercise(tmp_path):
    course, village = _pair(tmp_path)
    scene = village.scenes["bar-01"]
    turn = scene.turns[0]
    exercise = scenes.turn_exercise(scene, "s1", 0, turn)
    assert exercise.type == "build_sentence"
    assert exercise.solution == turn.solution
    assert exercise.distractors == turn.distractors
    assert exercise.id == "bar-01:s1#0"


def test_picks_a_scene_that_was_never_played(conn, tmp_path):
    course, village = _pair(tmp_path)
    game_repo.record_run(conn, scene_id="bar-01", seed="s1", played_at="2026-09-08T10:00:00")
    scene, seed = scenes.pick_scene(
        village, conn, place_id="magazin", npc_id=None, now="2026-09-08T11:00:00"
    )
    assert scene.id == "magazin-01"
    assert seed


def test_picks_the_least_recently_played_scene(conn, tmp_path):
    course, village = _pair(tmp_path)
    game_repo.record_run(conn, scene_id="bar-01", seed="s1", played_at="2026-09-08T10:00:00")
    scene, _ = scenes.pick_scene(
        village, conn, place_id="bar", npc_id="pjotr", now="2026-09-08T12:00:00"
    )
    assert scene.id == "bar-01"


def test_pick_scene_prefers_never_played_then_the_oldest_played(conn, tmp_path):
    village = load_village(
        write_village(
            tmp_path,
            scenes=[_dialog_scene("bar-01"), _dialog_scene("bar-02"), _dialog_scene("bar-03")],
        )
    )
    game_repo.record_run(conn, scene_id="bar-02", seed="s1", played_at="2026-09-01T10:00:00")
    game_repo.record_run(conn, scene_id="bar-03", seed="s1", played_at="2026-09-05T10:00:00")

    scene, _ = scenes.pick_scene(
        village, conn, place_id="bar", npc_id="pjotr", now="2026-09-08T11:00:00"
    )
    assert scene.id == "bar-01"  # nie gespielt schlägt jede gespielte Szene

    game_repo.record_run(conn, scene_id="bar-01", seed="s2", played_at="2026-09-08T11:00:00")
    scene, _ = scenes.pick_scene(
        village, conn, place_id="bar", npc_id="pjotr", now="2026-09-08T12:00:00"
    )
    assert scene.id == "bar-02"  # unter den gespielten gewinnt die älteste


def test_pick_scene_breaks_ties_between_never_played_scenes_by_id(conn, tmp_path):
    village = load_village(
        write_village(tmp_path, scenes=[_dialog_scene("bar-b"), _dialog_scene("bar-a")])
    )
    scene, _ = scenes.pick_scene(
        village, conn, place_id="bar", npc_id="pjotr", now="2026-09-08T11:00:00"
    )
    assert scene.id == "bar-a"
