import json
from pathlib import Path

MINIMAL_PLACES = [
    {
        "id": "bar",
        "name_ru": "бар",
        "name_de": "Bar",
        "kind": "npcs",
        "art": "bar",
        "hotspot": {"x": 0.1, "y": 0.5, "w": 0.2, "h": 0.2},
    },
    {
        "id": "magazin",
        "name_ru": "магази́н",
        "name_de": "Laden",
        "kind": "shopping",
        "art": "magazin",
        "hotspot": {"x": 0.5, "y": 0.5, "w": 0.2, "h": 0.2},
    },
]

MINIMAL_NPCS = [
    {
        "id": "pjotr",
        "name_ru": "Пётр",
        "name_de": "Pjotr",
        "place": "bar",
        "about_de": "Sitzt jeden Abend am selben Platz.",
        "art": "npc_pjotr",
    },
    {
        "id": "prodavshchitsa",
        "name_ru": "Ни́на",
        "name_de": "Nina",
        "place": "magazin",
        "about_de": "Führt den Laden seit dreißig Jahren.",
        "art": "npc_nina",
    },
]

MINIMAL_DIALOG = {
    "id": "bar-01",
    "kind": "dialog",
    "place": "bar",
    "npc": "pjotr",
    "title_de": "Der Mann am Tresen",
    "hint_unit": 15,
    "intro_de": "Ein älterer Mann dreht sich zu dir um.",
    "outro_de": "Pjotr nickt und wendet sich seinem Glas zu.",
    "turns": [
        {
            "npc_line": [["privet", "base"], ["kak", "base"], ["dela", "nom.pl"]],
            "prompt_de": "Sag, dass es dir gut geht, und frag zurück.",
            "solution": [["khorosho", "base"], ["a", "base"], ["ty", "nom"]],
            "distractors": [["plokho", "base"], ["vy", "nom"]],
        },
        {
            "npc_line": [["tozhe", "base"], ["khorosho", "base"]],
            "prompt_de": "Verabschiede dich locker.",
            "solution": [["poka", "base"]],
            "distractors": [["spasibo", "base"]],
        },
    ],
}

MINIMAL_SHOPPING = {
    "id": "magazin-01",
    "kind": "shopping",
    "place": "magazin",
    "npc": "prodavshchitsa",
    "title_de": "Einkaufen",
    "hint_unit": 27,
    "intro_de": "Nina schaut dich erwartungsvoll an.",
    "outro_de": "Nina reicht dir die Tüte.",
    "count": 2,
    "pool": [
        ["moloko", "acc.sg"],
        ["ryba", "acc.sg"],
        ["sup", "acc.sg"],
        ["voda", "acc.sg"],
    ],
    "ask_template": {
        "npc_line": [["chto", "acc"], ["vy", "nom"], ["khotet", "prs.2pl"]],
        "prompt_de": "Frag nach: {item}",
        "solution": [["ja", "nom"], ["khotet", "prs.1sg"], "{item}", ["pozhalujsta", "base"]],
    },
    "closing_turn": {
        "npc_line": [["eto", "base"], ["stoit", "prs.3sg"], ["pjat", "nom"], ["evro", "gen.pl"]],
        "prompt_de": "Bezahl mit Karte und bedank dich.",
        "solution": [["karta", "nom.sg"], ["pozhalujsta", "base"]],
        "distractors": [["dengi", "nom.pl"], ["spasibo", "base"]],
    },
}


def write_village(root, *, places=None, npcs=None, scenes=None) -> Path:
    """Write a village tree under root and return the game directory."""
    game = Path(root) / "game"
    (game / "scenes").mkdir(parents=True, exist_ok=True)
    (game / "places.json").write_text(
        json.dumps({"version": 1, "places": places if places is not None else MINIMAL_PLACES}),
        encoding="utf-8",
    )
    (game / "npcs.json").write_text(
        json.dumps({"version": 1, "npcs": npcs if npcs is not None else MINIMAL_NPCS}),
        encoding="utf-8",
    )
    for scene in scenes if scenes is not None else [MINIMAL_DIALOG, MINIMAL_SHOPPING]:
        (game / "scenes" / f"{scene['id']}.json").write_text(
            json.dumps(scene), encoding="utf-8"
        )
    return game
