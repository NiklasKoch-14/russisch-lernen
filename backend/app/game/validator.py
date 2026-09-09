from pathlib import Path

from app.content.models import Course
from app.content.validation import check_token as _check_token
from app.game.art import art_path
from app.game.models import Scene, Turn, Village

MIN_TURNS = 2
PLACE_KINDS = frozenset({"course", "npcs", "shopping"})
SCENE_KINDS = frozenset({"dialog", "shopping"})


def _check_turn(course: Course, turn: Turn, where: str) -> list[str]:
    errors: list[str] = []
    for token in turn.npc_line + turn.solution + turn.distractors:
        errors.extend(_check_token(course, token, where))
    if not turn.prompt_de.strip():
        errors.append(f"{where}: prompt_de ist leer")
    overlap = set(turn.distractors) & set(turn.solution)
    if overlap:
        errors.append(f"{where}: Ablenker {sorted(overlap)} sind Teil der Lösung")
    return errors


def _check_scene(course: Course, village: Village, scene: Scene) -> list[str]:
    where = f"Szene {scene.id}"
    errors: list[str] = []

    if scene.kind not in SCENE_KINDS:
        errors.append(f"{where}: unbekannte Szenenart {scene.kind!r}")
    if scene.place not in village.places:
        errors.append(f"{where}: Ort {scene.place!r} gibt es nicht")
    if scene.npc not in village.npcs:
        errors.append(f"{where}: Person {scene.npc!r} gibt es nicht")
    if scene.hint_unit not in course.units:
        errors.append(f"{where}: hint_unit {scene.hint_unit} verweist auf keine Einheit")

    if scene.kind == "dialog":
        if len(scene.turns) < MIN_TURNS:
            errors.append(f"{where}: braucht mindestens zwei Züge, hat {len(scene.turns)}")
        for index, turn in enumerate(scene.turns):
            errors.extend(_check_turn(course, turn, f"{where}, Zug {index}"))

    if scene.kind == "shopping":
        if scene.ask_template is None:
            errors.append(f"{where}: shopping braucht ein ask_template")
        else:
            slots = sum(1 for item in scene.ask_template.solution if item is None)
            if slots != 1:
                errors.append(
                    f"{where}: die Lösungsvorlage braucht genau einen {{item}}-Platz, hat {slots}"
                )
            for token in scene.ask_template.npc_line:
                errors.extend(_check_token(course, token, f"{where}, Vorlage"))
            for token in scene.ask_template.solution:
                if token is not None:
                    errors.extend(_check_token(course, token, f"{where}, Vorlage"))
            if "{item}" not in scene.ask_template.prompt_de:
                errors.append(f"{where}: prompt_de der Vorlage enthält kein {{item}}")
        if scene.count >= len(scene.pool):
            errors.append(
                f"{where}: der Pool muss größer sein als count "
                f"({scene.count} von {len(scene.pool)}) — sonst gibt es keine Ablenker"
            )
        for token in scene.pool:
            errors.extend(_check_token(course, token, f"{where}, Pool"))
        if scene.closing_turn is not None:
            errors.extend(_check_turn(course, scene.closing_turn, f"{where}, Schlusszug"))

    return errors


def _check_rect(rect, where: str, label: str) -> list[str]:
    """Ein Anteils-Rechteck muss im Bild liegen — für Klickflächen wie für Standorte."""
    if any(value < 0 or value > 1 for value in (rect.x, rect.y, rect.w, rect.h)):
        return [f"{where}: {label} liegt außerhalb von 0 bis 1"]
    if rect.x + rect.w > 1 or rect.y + rect.h > 1:
        return [f"{where}: {label} ragt über das Bild hinaus"]
    return []


def _check_places(village: Village) -> list[str]:
    errors: list[str] = []
    for place in village.places.values():
        if place.kind not in PLACE_KINDS:
            errors.append(f"Ort {place.id}: unbekannte Art {place.kind!r}")
        errors.extend(_check_rect(place.hotspot, f"Ort {place.id}", "Klickfläche"))

    ordered = sorted(village.places.values(), key=lambda place: place.id)
    for index, first in enumerate(ordered):
        for second in ordered[index + 1 :]:
            if _overlap(first.hotspot, second.hotspot):
                errors.append(
                    f"Orte {first.id} und {second.id}: ihre Klickflächen überlappen sich"
                )
    return errors


def _overlap(first, second) -> bool:
    return (
        first.x < second.x + second.w
        and second.x < first.x + first.w
        and first.y < second.y + second.h
        and second.y < first.y + first.h
    )


def _check_npcs(village: Village) -> list[str]:
    errors: list[str] = []
    for npc in sorted(village.npcs.values(), key=lambda npc: npc.id):
        place = village.places.get(npc.place)
        if place is None:
            errors.append(f"Person {npc.id}: Ort {npc.place!r} gibt es nicht")
            continue
        # An einem Personen-Ort wird die Figur im Raumbild angeklickt. Ohne
        # Platz stünde sie nirgends und wäre nur über die Rückfall-Liste
        # erreichbar.
        if place.kind == "npcs" and npc.spot is None:
            errors.append(
                f"Person {npc.id}: braucht einen Platz im Raum, "
                f"weil man am Ort {place.id} Personen anklickt"
            )
        if npc.spot is not None:
            errors.extend(_check_rect(npc.spot, f"Person {npc.id}", "Platz"))

    for place_id in sorted(village.places):
        standing = sorted(
            (npc for npc in village.npcs_at(place_id) if npc.spot is not None),
            key=lambda npc: npc.id,
        )
        for index, first in enumerate(standing):
            for second in standing[index + 1 :]:
                if _overlap(first.spot, second.spot):
                    errors.append(
                        f"Personen {first.id} und {second.id} in {place_id}: "
                        "ihre Plätze überlappen sich, eine von beiden ist nicht anklickbar"
                    )
    return errors


def _check_art(village: Village, art_dir: Path) -> list[str]:
    errors: list[str] = []
    for place in sorted(village.places.values(), key=lambda place: place.id):
        if art_path(art_dir, place.art) is None:
            errors.append(f"Ort {place.id}: zum Bild {place.art!r} gibt es keine Datei")
    for npc in sorted(village.npcs.values(), key=lambda npc: npc.id):
        if art_path(art_dir, npc.art) is None:
            errors.append(f"Person {npc.id}: zum Bild {npc.art!r} gibt es keine Datei")
    if art_path(art_dir, "village") is None:
        errors.append("Zur Dorfkarte 'village' gibt es keine Datei")
    return errors


def validate_village(course: Course, village: Village, art_dir: Path | None = None) -> list[str]:
    """Return every village rule violation as a German message; empty means valid."""
    errors = _check_places(village) + _check_npcs(village)
    for scene in sorted(village.scenes.values(), key=lambda scene: scene.id):
        errors.extend(_check_scene(course, village, scene))
    if art_dir is not None:
        errors.extend(_check_art(village, art_dir))
    return errors
