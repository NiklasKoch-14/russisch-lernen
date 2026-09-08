from sqlite3 import Connection

from app.content.models import BuildSentenceExercise, Course
from app.course.shuffle import shuffled_order
from app.game.models import Scene, Turn, Village
from app.repositories import game_repo

MAX_SHOPPING_DISTRACTORS = 2


def _shopping_turns(course: Course, scene: Scene, seed: str) -> list[Turn]:
    template = scene.ask_template
    order = shuffled_order(f"{scene.id}:{seed}", len(scene.pool))
    picked = [scene.pool[position] for position in order[: scene.count]]
    unused = [scene.pool[position] for position in order[scene.count :]]

    turns: list[Turn] = []
    for index, item in enumerate(picked):
        # Je Zug eine eigene Ziehung aus den übrigen Waren, sonst sieht der
        # Lernende nach dem ersten Zug, welche Kachel nie die Lösung ist.
        distractor_order = shuffled_order(f"{scene.id}:{seed}:distractors:{index}", len(unused))
        distractors = [unused[position] for position in distractor_order[:MAX_SHOPPING_DISTRACTORS]]
        turns.append(
            Turn(
                npc_line=list(template.npc_line),
                prompt_de=template.prompt_de.replace("{item}", course.gloss(item)),
                solution=[item if ref is None else ref for ref in template.solution],
                distractors=distractors,
            )
        )
    if scene.closing_turn is not None:
        turns.append(scene.closing_turn)
    return turns


def scene_turns(course: Course, scene: Scene, seed: str) -> list[Turn]:
    """Die Züge einer Szene — bei shopping aus dem Seed zusammengesetzt."""
    if scene.kind == "shopping":
        return _shopping_turns(course, scene, seed)
    return list(scene.turns)


def turn_exercise(scene: Scene, seed: str, index: int, turn: Turn) -> BuildSentenceExercise:
    """Einen Zug als Kachelaufgabe — damit presenter und checker unverändert greifen.

    Die Id geht in das Mischen der Kacheln ein und muss deshalb den Seed
    enthalten: derselbe Zug mit anderem Einkaufszettel soll anders liegen.
    """
    return BuildSentenceExercise(
        id=f"{scene.id}:{seed}#{index}",
        prompt_de=turn.prompt_de,
        solution=list(turn.solution),
        distractors=list(turn.distractors),
    )


def pick_scene(
    village: Village, conn: Connection, *, place_id: str, npc_id: str | None, now: str
) -> tuple[Scene, str]:
    """Die am längsten nicht gespielte Szene des Ortes, dazu ein frischer Seed."""
    candidates = village.scenes_at(place_id, npc_id)
    if not candidates:
        raise KeyError(f"Zu {place_id!r} gibt es keine Szene")
    played = game_repo.last_played(conn)
    candidates.sort(key=lambda scene: (played.get(scene.id, ""), scene.id))
    scene = candidates[0]
    return scene, f"{scene.id}:{now}"
