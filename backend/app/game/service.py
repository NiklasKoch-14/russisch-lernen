from sqlite3 import Connection

from app.content.models import Course, TokenRef
from app.course.checker import check_answer
from app.course.presenter import present_exercise, spoken_text
from app.course.service import schedule_form
from app.game import scenes
from app.game.models import Hotspot, Npc, Scene, Turn, Village
from app.repositories import game_repo, progress_repo

NPC_CONFUSED: list[TokenRef] = [("izvinit", "imp.pl")]
"""Was der NPC sagt, wenn er nicht versteht — «Извини́те?»"""


def _npc_of(village: Village, scene: Scene) -> Npc:
    """Die Person einer Szene — mit einer lesbaren Meldung, wenn es sie nicht gibt.

    Der Lader prueft Szenen nicht gegen die Personenliste, das tut nur
    `make validate`. Fehlerhafter Inhalt darf hier deshalb nicht als nacktes
    KeyError durchschlagen: die Routen machen daraus einen 404 und zeigen den
    Text an.
    """
    try:
        return village.npcs[scene.npc]
    except KeyError as exc:
        raise KeyError(f"Zu Szene {scene.id!r} gibt es die Person {scene.npc!r} nicht") from exc


def _line(course: Course, refs: list[TokenRef]) -> dict:
    return {
        "text": " ".join(course.form(ref).text for ref in refs),
        "translit": " ".join(course.form(ref).translit for ref in refs),
        "audio_text": spoken_text(course, refs),
    }


def _turn_at(scene_id: str, turns: list[Turn], index: int) -> Turn:
    """Den Zug an `index` holen — negative Indizes würden sonst still den
    letzten Zug liefern (Python-Slicing), mit falscher Kachel-Id und ohne dass
    `scene_completed` je zutrifft."""
    if not 0 <= index < len(turns):
        raise IndexError(
            f"Szene {scene_id!r} hat keinen Zug mit Index {index} (0..{len(turns) - 1})"
        )
    return turns[index]


def _rect_payload(rect: Hotspot | None) -> dict | None:
    """Ein Anteils-Rechteck für den Client, oder None — dann steht die Person nirgends."""
    if rect is None:
        return None
    return {"x": rect.x, "y": rect.y, "w": rect.w, "h": rect.h}


def village_payload(village: Village) -> dict:
    return {
        "places": [
            {
                "id": place.id,
                "name_ru": place.name_ru,
                "name_de": place.name_de,
                "kind": place.kind,
                "art": place.art,
                "hotspot": _rect_payload(place.hotspot),
            }
            for place in sorted(village.places.values(), key=lambda place: place.id)
        ]
    }


def _next_unit_id(course: Course, conn: Connection) -> int | None:
    progress = progress_repo.all_progress(conn)
    for unit in course.ordered_units():
        entry = progress.get(unit.id)
        if entry is None or entry.status != "completed":
            return unit.id
    return None


def place_payload(village: Village, course: Course, conn: Connection, place_id: str) -> dict:
    place = village.places[place_id]
    payload = {
        "id": place.id,
        "name_ru": place.name_ru,
        "name_de": place.name_de,
        "kind": place.kind,
        "art": place.art,
        "npcs": [
            {
                "id": npc.id,
                "name_ru": npc.name_ru,
                "name_de": npc.name_de,
                "about_de": npc.about_de,
                "art": npc.art,
                "spot": _rect_payload(npc.spot),
            }
            for npc in sorted(village.npcs_at(place_id), key=lambda npc: npc.id)
        ],
    }
    if place.kind == "course":
        payload["next_unit_id"] = _next_unit_id(course, conn)
    return payload


def start_scene(
    village: Village,
    course: Course,
    conn: Connection,
    *,
    place_id: str,
    npc_id: str | None,
    now: str,
) -> dict:
    scene, seed = scenes.pick_scene(
        village, conn, place_id=place_id, npc_id=npc_id, now=now
    )
    npc = _npc_of(village, scene)
    return {
        "scene_id": scene.id,
        "seed": seed,
        "title_de": scene.title_de,
        "intro_de": scene.intro_de,
        "hint_unit": scene.hint_unit,
        "npc": {"id": npc.id, "name_ru": npc.name_ru, "name_de": npc.name_de, "art": npc.art},
        # Bei shopping haengt die Zahl der Zuege vom Seed ab, deshalb wird sie
        # gerechnet statt aus der Szene gelesen.
        "turn_count": len(scenes.scene_turns(course, scene, seed)),
    }


def turn_payload(
    course: Course, village: Village, *, scene_id: str, seed: str, index: int
) -> dict:
    scene = village.scenes[scene_id]
    turns = scenes.scene_turns(course, scene, seed)
    turn = _turn_at(scene_id, turns, index)
    exercise = scenes.turn_exercise(scene, seed, index, turn)
    npc = _npc_of(village, scene)
    return {
        "index": index,
        "turn_count": len(turns),
        "npc": {"id": npc.id, "name_ru": npc.name_ru, "name_de": npc.name_de, "art": npc.art},
        "npc_line": _line(course, turn.npc_line),
        "exercise": present_exercise(course, exercise),
    }


def answer_turn(
    conn: Connection,
    course: Course,
    village: Village,
    *,
    scene_id: str,
    seed: str,
    index: int,
    submission: dict,
    today: str,
    now: str,
) -> dict:
    scene = village.scenes[scene_id]
    turns = scenes.scene_turns(course, scene, seed)
    turn = _turn_at(scene_id, turns, index)
    exercise = scenes.turn_exercise(scene, seed, index, turn)
    result = check_answer(course, exercise, submission)

    for ref in result.trained_forms:
        schedule_form(conn, ref, correct=result.correct, today=today)

    completed = index == len(turns) - 1
    if completed:
        game_repo.record_run(conn, scene_id=scene.id, seed=seed, played_at=now)

    return {
        "correct": result.correct,
        "solution_text": result.solution_text,
        "solution_translit": result.solution_translit,
        "solution_audio": result.solution_audio,
        "explanation_de": result.explanation_de,
        "npc_reaction": None if result.correct else _line(course, NPC_CONFUSED),
        "scene_completed": completed,
        "outro_de": scene.outro_de if completed else "",
    }
