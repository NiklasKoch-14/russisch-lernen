from pathlib import Path

from app.content.jsonio import ContentError, _read_json, _token, _tokens
from app.game.models import AskTemplate, Hotspot, Npc, Place, Scene, Turn, Village

ITEM_SLOT = "{item}"


def _turn(raw: dict, where: str) -> Turn:
    try:
        return Turn(
            npc_line=_tokens(raw["npc_line"], where),
            prompt_de=raw["prompt_de"],
            solution=_tokens(raw["solution"], where),
            distractors=_tokens(raw.get("distractors", []), where),
        )
    except KeyError as exc:
        raise ContentError(f"{where}: Feld fehlt {exc}") from exc


def _ask_template(raw: dict, where: str) -> AskTemplate:
    try:
        return AskTemplate(
            npc_line=_tokens(raw["npc_line"], where),
            prompt_de=raw["prompt_de"],
            solution=[
                None if item == ITEM_SLOT else _token(item, where) for item in raw["solution"]
            ],
        )
    except KeyError as exc:
        raise ContentError(f"{where}: Feld fehlt {exc}") from exc


def _scene(raw: dict, source: Path) -> Scene:
    if raw.get("id") != source.stem:
        raise ContentError(
            f"{source.name}: die Szenen-Id {raw.get('id')!r} passt nicht zum Dateinamen"
        )
    where = f"Szene {raw['id']}"
    try:
        return Scene(
            id=raw["id"],
            kind=raw["kind"],
            place=raw["place"],
            npc=raw["npc"],
            title_de=raw["title_de"],
            hint_unit=int(raw["hint_unit"]),
            intro_de=raw.get("intro_de", ""),
            outro_de=raw.get("outro_de", ""),
            turns=[_turn(item, where) for item in raw.get("turns", [])],
            count=int(raw.get("count", 0)),
            pool=_tokens(raw.get("pool", []), where),
            ask_template=(
                _ask_template(raw["ask_template"], where) if "ask_template" in raw else None
            ),
            closing_turn=_turn(raw["closing_turn"], where) if "closing_turn" in raw else None,
        )
    except KeyError as exc:
        raise ContentError(f"{source.name}: Feld fehlt {exc}") from exc


def _rect(raw: dict) -> Hotspot:
    """Ein Anteils-Rechteck aus dem JSON — Klickfläche eines Ortes oder Platz einer Person."""
    return Hotspot(
        x=float(raw["x"]), y=float(raw["y"]), w=float(raw["w"]), h=float(raw["h"])
    )


def load_village(game_dir: str | Path) -> Village:
    """Load the whole village package from disk into an immutable Village."""
    root = Path(game_dir)

    raw_places = _read_json(root / "places.json")
    places = {}
    for item in raw_places["places"]:
        places[item["id"]] = Place(
            id=item["id"],
            name_ru=item["name_ru"],
            name_de=item["name_de"],
            kind=item["kind"],
            art=item["art"],
            hotspot=_rect(item["hotspot"]),
        )

    raw_npcs = _read_json(root / "npcs.json")
    npcs = {
        item["id"]: Npc(
            id=item["id"],
            name_ru=item["name_ru"],
            name_de=item["name_de"],
            place=item["place"],
            about_de=item["about_de"],
            art=item["art"],
            spot=_rect(item["spot"]) if item.get("spot") is not None else None,
        )
        for item in raw_npcs["npcs"]
    }

    scenes = {}
    for path in sorted((root / "scenes").glob("*.json")):
        scene = _scene(_read_json(path), path)
        scenes[scene.id] = scene

    return Village(places=places, npcs=npcs, scenes=scenes)
