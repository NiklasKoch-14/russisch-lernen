# Dorf-Rollenspielebene — Umsetzungsplan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Eine begehbare Dorfkarte neben dem Kurs, auf der NPCs Gespräche führen, die der Lernende aus Wortkacheln beantwortet.

**Architecture:** Eigene Inhaltsschicht unter `content/game/`, geladen wie der Kurs. Ein Gesprächszug wird zur Laufzeit in eine `BuildSentenceExercise` übersetzt, sodass `course/presenter.py` und `course/checker.py` unverändert weiterbenutzt werden. Szenen laufen zustandslos: sie sind vollständig bestimmt durch `(scene_id, seed)`.

**Tech Stack:** Python 3.14, FastAPI, SQLite, pytest — React 18, TypeScript, Vite, Tailwind, Vitest, Playwright.

**Spec:** `docs/superpowers/specs/2026-09-08-speaker-village-roleplay-design.md`

## Global Constraints

- Alle nutzersichtbaren Texte, Kommentare und Commit-Nachrichten auf Deutsch; Bezeichner im Code englisch.
- Lösungen verlassen den Server nie. Der Client bekommt Kachel-Indizes und schickt Indizes zurück.
- Kein Sprachmodell erzeugt Lerninhalt. Szenen sind kuratiertes JSON.
- Sätze referenzieren `(lexeme_id, form_key)`-Paare, niemals rohe Zeichenketten.
- Klickflächen sind Anteile von 0 bis 1 auf einer Fläche im Verhältnis **16:9**.
- Neue Tabellen additiv in `SCHEMA` von `backend/app/db.py` mit `CREATE TABLE IF NOT EXISTS`.
- Tests laufen mit `cd backend && .venv/bin/pytest -q -p no:cacheprovider` beziehungsweise `cd frontend && npx vitest run`.
- Für eigene Prüfläufe **immer** `make test-e2e` (headless), nie `make test-e2e-show`.

---

### Task 1: Modelle und Loader für das Dorf

**Files:**
- Create: `backend/app/game/__init__.py`
- Create: `backend/app/game/models.py`
- Create: `backend/app/game/loader.py`
- Create: `backend/tests/village_factory.py`
- Create: `backend/tests/test_village_loader.py`
- Create: `content/game/places.json`
- Create: `content/game/npcs.json`
- Create: `content/game/scenes/bar-01.json`
- Create: `content/game/scenes/magazin-01.json`

**Interfaces:**
- Consumes: `app.content.models.TokenRef`, `app.content.loader.ContentError`
- Produces: `Hotspot`, `Place`, `Npc`, `Turn`, `AskTemplate`, `Scene`, `Village`; `load_village(game_dir: str | Path) -> Village`; `write_village(root, *, places=None, npcs=None, scenes=None) -> Path`

- [ ] **Step 1: Write the failing test**

`backend/tests/village_factory.py`:

```python
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
```

`backend/tests/test_village_loader.py`:

```python
import pytest

from app.content.loader import ContentError
from app.game.loader import load_village
from tests.village_factory import MINIMAL_DIALOG, write_village


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
```

Der Import von `MINIMAL_DIALOG` wird in diesem Test nicht gebraucht — lass ihn weg, wenn `ruff` ihn anmahnt.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && .venv/bin/pytest tests/test_village_loader.py -q -p no:cacheprovider`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.game'`

- [ ] **Step 3: Write the models**

`backend/app/game/__init__.py`: leer.

`backend/app/game/models.py`:

```python
from dataclasses import dataclass, field

from app.content.models import TokenRef


@dataclass(frozen=True)
class Hotspot:
    """Klickfläche als Anteil der Kartenbreite und -höhe, Bezugsformat 16:9."""

    x: float
    y: float
    w: float
    h: float


@dataclass(frozen=True)
class Place:
    id: str
    name_ru: str
    name_de: str
    kind: str
    """course = führt in die nächste Einheit, npcs = Personenauswahl, shopping = Einkaufszettel."""
    art: str
    hotspot: Hotspot


@dataclass(frozen=True)
class Npc:
    id: str
    name_ru: str
    name_de: str
    place: str
    about_de: str
    art: str


@dataclass(frozen=True)
class Turn:
    npc_line: list[TokenRef]
    prompt_de: str
    solution: list[TokenRef]
    distractors: list[TokenRef]


@dataclass(frozen=True)
class AskTemplate:
    """Vorlage für einen Einkaufszug. None in `solution` ist der Platz der Ware."""

    npc_line: list[TokenRef]
    prompt_de: str
    solution: list[TokenRef | None]


@dataclass(frozen=True)
class Scene:
    id: str
    kind: str
    """dialog = ausgeschriebene Züge, shopping = aus dem Pool zusammengesetzt."""
    place: str
    npc: str
    title_de: str
    hint_unit: int
    intro_de: str = ""
    outro_de: str = ""
    turns: list[Turn] = field(default_factory=list)
    count: int = 0
    pool: list[TokenRef] = field(default_factory=list)
    ask_template: AskTemplate | None = None
    closing_turn: Turn | None = None


@dataclass(frozen=True)
class Village:
    places: dict[str, Place]
    npcs: dict[str, Npc]
    scenes: dict[str, Scene]

    def npcs_at(self, place_id: str) -> list[Npc]:
        return [npc for npc in self.npcs.values() if npc.place == place_id]

    def scenes_at(self, place_id: str, npc_id: str | None = None) -> list[Scene]:
        return [
            scene
            for scene in self.scenes.values()
            if scene.place == place_id and (npc_id is None or scene.npc == npc_id)
        ]
```

`backend/app/game/loader.py`:

```python
import json
from pathlib import Path

from app.content.loader import ContentError
from app.content.models import TokenRef
from app.game.models import AskTemplate, Hotspot, Npc, Place, Scene, Turn, Village

ITEM_SLOT = "{item}"


def _read_json(path: Path) -> dict:
    if not path.exists():
        raise ContentError(f"Datei fehlt: {path.name} ({path})")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ContentError(f"Ungültiges JSON in {path.name}: {exc}") from exc


def _token(raw: object, where: str) -> TokenRef:
    if not isinstance(raw, list) or len(raw) != 2:
        raise ContentError(f"Token in {where} muss [lexeme_id, form_key] sein, war: {raw!r}")
    return (str(raw[0]), str(raw[1]))


def _tokens(raw: object, where: str) -> list[TokenRef]:
    if not isinstance(raw, list):
        raise ContentError(f"Tokenliste in {where} muss eine Liste sein, war: {raw!r}")
    return [_token(item, where) for item in raw]


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


def load_village(game_dir: str | Path) -> Village:
    """Load the whole village package from disk into an immutable Village."""
    root = Path(game_dir)

    raw_places = _read_json(root / "places.json")
    places = {}
    for item in raw_places["places"]:
        spot = item["hotspot"]
        places[item["id"]] = Place(
            id=item["id"],
            name_ru=item["name_ru"],
            name_de=item["name_de"],
            kind=item["kind"],
            art=item["art"],
            hotspot=Hotspot(
                x=float(spot["x"]), y=float(spot["y"]),
                w=float(spot["w"]), h=float(spot["h"]),
            ),
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
        )
        for item in raw_npcs["npcs"]
    }

    scenes = {}
    for path in sorted((root / "scenes").glob("*.json")):
        scene = _scene(_read_json(path), path)
        scenes[scene.id] = scene

    return Village(places=places, npcs=npcs, scenes=scenes)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && .venv/bin/pytest tests/test_village_loader.py -q -p no:cacheprovider`
Expected: PASS (8 tests)

- [ ] **Step 5: Write the real content files**

`content/game/places.json` — vier Orte. Die Klickflächen müssen später zur gezeichneten Karte passen; diese Werte sind die Vorgabe, an der sich Task 5 beim Zeichnen orientiert.

```json
{
  "version": 1,
  "places": [
    { "id": "shkola", "name_ru": "шко́ла", "name_de": "Sprachkurs", "kind": "course",
      "art": "shkola", "hotspot": { "x": 0.08, "y": 0.30, "w": 0.18, "h": 0.30 } },
    { "id": "kafe", "name_ru": "кафе́", "name_de": "Café", "kind": "npcs",
      "art": "kafe", "hotspot": { "x": 0.30, "y": 0.34, "w": 0.18, "h": 0.28 } },
    { "id": "magazin", "name_ru": "магази́н", "name_de": "Laden", "kind": "shopping",
      "art": "magazin", "hotspot": { "x": 0.52, "y": 0.32, "w": 0.18, "h": 0.30 } },
    { "id": "bar", "name_ru": "бар", "name_de": "Bar", "kind": "npcs",
      "art": "bar", "hotspot": { "x": 0.74, "y": 0.36, "w": 0.18, "h": 0.28 } }
  ]
}
```

`content/game/npcs.json` — zwei Personen für den Anfang, der Rest kommt in Task 12:

```json
{
  "version": 1,
  "npcs": [
    { "id": "pjotr", "name_ru": "Пётр", "name_de": "Pjotr", "place": "bar",
      "about_de": "Sitzt jeden Abend am selben Platz und fragt jeden Neuen aus.",
      "art": "npc_pjotr" },
    { "id": "nina", "name_ru": "Ни́на", "name_de": "Nina", "place": "magazin",
      "about_de": "Führt den Laden seit dreißig Jahren.", "art": "npc_nina" }
  ]
}
```

`content/game/scenes/bar-01.json`: der Inhalt von `MINIMAL_DIALOG` aus Step 1, unverändert.

`content/game/scenes/magazin-01.json`: der Inhalt von `MINIMAL_SHOPPING` aus Step 1, aber mit `"npc": "nina"` statt `"prodavshchitsa"` und `"count": 3`.

- [ ] **Step 6: Verify the real content loads**

Run:

```bash
cd backend && .venv/bin/python -c "
from app.game.loader import load_village
v = load_village('../content/game')
print(len(v.places), 'Orte,', len(v.npcs), 'Personen,', len(v.scenes), 'Szenen')
"
```

Expected: `4 Orte, 2 Personen, 2 Szenen`

- [ ] **Step 7: Commit**

```bash
git add backend/app/game backend/tests/village_factory.py backend/tests/test_village_loader.py content/game
git commit -m "feat(game): load the village content package"
```

---

### Task 2: Validator für das Dorf

**Files:**
- Create: `backend/app/game/validator.py`
- Create: `backend/tests/test_village_validator.py`
- Modify: `backend/scripts/validate_content.py`

**Interfaces:**
- Consumes: `load_village`, `Village`, `app.content.models.Course`
- Produces: `validate_village(course: Course, village: Village) -> list[str]`

Die Regel „zu jedem `art`-Verweis existiert eine Datei" (Regel 8 der Spec) kommt erst in Task 5 dazu — vorher gibt es die Bilder noch nicht.

- [ ] **Step 1: Write the failing test**

`backend/tests/test_village_validator.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && .venv/bin/pytest tests/test_village_validator.py -q -p no:cacheprovider`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.game.validator'`

- [ ] **Step 3: Write the validator**

`backend/app/game/validator.py`:

```python
from app.content.models import Course, TokenRef
from app.game.models import Scene, Turn, Village

MIN_TURNS = 2
PLACE_KINDS = frozenset({"course", "npcs", "shopping"})
SCENE_KINDS = frozenset({"dialog", "shopping"})


def _check_token(course: Course, token: TokenRef, where: str) -> list[str]:
    lexeme_id, form_key = token
    lexeme = course.lexemes.get(lexeme_id)
    if lexeme is None:
        return [f"{where}: Lexem {lexeme_id!r} existiert nicht im Lexikon"]
    if form_key not in lexeme.forms:
        return [f"{where}: Lexem {lexeme_id!r} hat keine Form {form_key!r}"]
    return []


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


def _check_places(village: Village) -> list[str]:
    errors: list[str] = []
    for place in village.places.values():
        if place.kind not in PLACE_KINDS:
            errors.append(f"Ort {place.id}: unbekannte Art {place.kind!r}")
        spot = place.hotspot
        values = (spot.x, spot.y, spot.w, spot.h)
        if any(value < 0 or value > 1 for value in values):
            errors.append(f"Ort {place.id}: Klickfläche liegt außerhalb von 0 bis 1")
        elif spot.x + spot.w > 1 or spot.y + spot.h > 1:
            errors.append(f"Ort {place.id}: Klickfläche ragt über die Karte hinaus")

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
    return [
        f"Person {npc.id}: Ort {npc.place!r} gibt es nicht"
        for npc in village.npcs.values()
        if npc.place not in village.places
    ]


def validate_village(course: Course, village: Village) -> list[str]:
    """Return every village rule violation as a German message; empty means valid."""
    errors = _check_places(village) + _check_npcs(village)
    for scene in sorted(village.scenes.values(), key=lambda scene: scene.id):
        errors.extend(_check_scene(course, village, scene))
    return errors
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && .venv/bin/pytest tests/test_village_validator.py -q -p no:cacheprovider`
Expected: PASS (11 tests)

- [ ] **Step 5: Wire the village into `make validate`**

`backend/scripts/validate_content.py` — vollständig ersetzen:

```python
"""Validate the course and village content. Usage: python -m scripts.validate_content [dir]"""
import sys
from pathlib import Path

from app.content.loader import ContentError, load_course
from app.content.validator import validate_course
from app.game.loader import load_village
from app.game.validator import validate_village

ROOT = Path(__file__).resolve().parents[2] / "content"
DEFAULT_DIR = ROOT / "ru"
DEFAULT_GAME_DIR = ROOT / "game"


def main(argv: list[str]) -> int:
    content_dir = Path(argv[1]) if len(argv) > 1 else DEFAULT_DIR
    game_dir = content_dir.parent / "game"
    try:
        course = load_course(content_dir)
        village = load_village(game_dir)
    except ContentError as exc:
        print(f"FEHLER beim Laden: {exc}")
        return 2

    errors = validate_course(course) + validate_village(course, village)
    if errors:
        print(f"{len(errors)} Problem(e) in {content_dir.parent}:")
        for error in errors:
            print(f"  - {error}")
        return 1

    print(
        f"OK — {len(course.units)} Einheiten, {len(course.lexemes)} Lexeme, "
        f"{len(course.screening)} Sonden, {len(village.places)} Orte, "
        f"{len(village.scenes)} Szenen"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
```

- [ ] **Step 6: Run the validator against the real content**

Run: `make validate`
Expected: `OK — 32 Einheiten, 204 Lexeme, 6 Sonden, 4 Orte, 2 Szenen`

Falls stattdessen Fehler erscheinen: die Beispielszenen aus Task 1 benutzen Lexeme, die im Kurs existieren müssen. Fehlende ergänzt man in `content/ru/lexicon.json` nach den Regeln der Kurs-Spec — nicht durch Abschalten der Regel.

- [ ] **Step 7: Commit**

```bash
git add backend/app/game/validator.py backend/tests/test_village_validator.py backend/scripts/validate_content.py
git commit -m "feat(game): validate the village against the lexicon"
```

---

### Task 3: Szenen auswählen und zusammensetzen

**Files:**
- Create: `backend/app/game/scenes.py`
- Create: `backend/app/repositories/game_repo.py`
- Create: `backend/tests/test_game_scenes.py`
- Create: `backend/tests/test_game_repo.py`
- Modify: `backend/app/db.py` (Tabelle in `SCHEMA`)

**Interfaces:**
- Consumes: `Village`, `Scene`, `Turn`, `Course`, `app.course.shuffle.shuffled_order`, `app.content.models.BuildSentenceExercise`
- Produces:
  - `game_repo.record_run(conn, *, scene_id: str, seed: str, played_at: str) -> None`
  - `game_repo.last_played(conn) -> dict[str, str]`
  - `scenes.scene_turns(course: Course, scene: Scene, seed: str) -> list[Turn]`
  - `scenes.turn_exercise(scene: Scene, seed: str, index: int, turn: Turn) -> BuildSentenceExercise`
  - `scenes.pick_scene(village: Village, conn, *, place_id: str, npc_id: str | None, now: str) -> tuple[Scene, str]`

- [ ] **Step 1: Write the failing test for the repository**

`backend/tests/test_game_repo.py`:

```python
from app.repositories import game_repo


def test_last_played_is_empty_initially(conn):
    assert game_repo.last_played(conn) == {}


def test_records_a_run_and_reports_its_time(conn):
    game_repo.record_run(conn, scene_id="bar-01", seed="s1", played_at="2026-09-08T10:00:00")
    assert game_repo.last_played(conn) == {"bar-01": "2026-09-08T10:00:00"}


def test_keeps_only_the_most_recent_time_per_scene(conn):
    game_repo.record_run(conn, scene_id="bar-01", seed="s1", played_at="2026-09-08T10:00:00")
    game_repo.record_run(conn, scene_id="bar-01", seed="s2", played_at="2026-09-09T10:00:00")
    assert game_repo.last_played(conn)["bar-01"] == "2026-09-09T10:00:00"
```

`conn` ist die vorhandene Fixture aus `backend/tests/conftest.py`.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && .venv/bin/pytest tests/test_game_repo.py -q -p no:cacheprovider`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.repositories.game_repo'`

- [ ] **Step 3: Add the table and the repository**

In `backend/app/db.py`, ans Ende des `SCHEMA`-Strings, vor die schließenden `"""`:

```sql
CREATE TABLE IF NOT EXISTS game_scene_runs (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    scene_id  TEXT NOT NULL,
    seed      TEXT NOT NULL,
    played_at TEXT NOT NULL
);
```

`backend/app/repositories/game_repo.py`:

```python
from sqlite3 import Connection


def record_run(conn: Connection, *, scene_id: str, seed: str, played_at: str) -> None:
    """Vermerken, dass eine Szene gespielt wurde — Grundlage der Szenenauswahl."""
    conn.execute(
        "INSERT INTO game_scene_runs (scene_id, seed, played_at) VALUES (?, ?, ?)",
        (scene_id, seed, played_at),
    )
    conn.commit()


def last_played(conn: Connection) -> dict[str, str]:
    """Je Szene der jüngste Spielzeitpunkt."""
    rows = conn.execute(
        "SELECT scene_id, MAX(played_at) AS played_at FROM game_scene_runs GROUP BY scene_id"
    ).fetchall()
    return {row["scene_id"]: row["played_at"] for row in rows}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && .venv/bin/pytest tests/test_game_repo.py -q -p no:cacheprovider`
Expected: PASS (3 tests)

- [ ] **Step 5: Write the failing test for scene assembly**

`backend/tests/test_game_scenes.py`:

```python
from pathlib import Path

from app.content.loader import load_course
from app.game import scenes
from app.game.loader import load_village
from app.repositories import game_repo
from tests.village_factory import write_village

REAL_CONTENT = Path(__file__).resolve().parents[2] / "content" / "ru"


def _pair(tmp_path):
    return load_course(REAL_CONTENT), load_village(write_village(tmp_path))


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
```

- [ ] **Step 6: Run test to verify it fails**

Run: `cd backend && .venv/bin/pytest tests/test_game_scenes.py -q -p no:cacheprovider`
Expected: FAIL with `ImportError: cannot import name 'scenes' from 'app.game'`

- [ ] **Step 7: Write the scene assembly**

`backend/app/game/scenes.py`:

```python
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
    for item in picked:
        turns.append(
            Turn(
                npc_line=list(template.npc_line),
                prompt_de=template.prompt_de.replace("{item}", course.gloss(item)),
                solution=[item if ref is None else ref for ref in template.solution],
                distractors=unused[:MAX_SHOPPING_DISTRACTORS],
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
```

- [ ] **Step 8: Run test to verify it passes**

Run: `cd backend && .venv/bin/pytest tests/test_game_scenes.py tests/test_game_repo.py -q -p no:cacheprovider`
Expected: PASS (12 tests)

- [ ] **Step 9: Commit**

```bash
git add backend/app/game/scenes.py backend/app/repositories/game_repo.py backend/app/db.py backend/tests/test_game_scenes.py backend/tests/test_game_repo.py
git commit -m "feat(game): pick and assemble scenes from a seed"
```

---

### Task 4: Payloads und Bewertung

**Files:**
- Create: `backend/app/game/service.py`
- Create: `backend/tests/test_game_service.py`

**Interfaces:**
- Consumes: `scenes.*`, `game_repo.*`, `app.course.presenter.present_exercise`, `app.course.presenter.spoken_text`, `app.course.checker.check_answer`, `app.course.service.schedule_form`, `app.repositories.progress_repo`
- Produces:
  - `village_payload(village: Village) -> dict`
  - `place_payload(village: Village, course: Course, conn, place_id: str) -> dict`
  - `start_scene(village: Village, course: Course, conn, *, place_id, npc_id, now) -> dict`
  - `turn_payload(course, village, *, scene_id, seed, index) -> dict`
  - `answer_turn(conn, course, village, *, scene_id, seed, index, submission, today, now) -> dict`

- [ ] **Step 1: Write the failing test**

`backend/tests/test_game_service.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && .venv/bin/pytest tests/test_game_service.py -q -p no:cacheprovider`
Expected: FAIL with `ImportError: cannot import name 'service' from 'app.game'`

- [ ] **Step 3: Write the service**

`backend/app/game/service.py`:

```python
from sqlite3 import Connection

from app.content.models import Course, TokenRef
from app.course.checker import check_answer
from app.course.presenter import present_exercise, spoken_text
from app.course.service import schedule_form
from app.game import scenes
from app.game.models import Village
from app.repositories import game_repo, progress_repo

NPC_CONFUSED: list[TokenRef] = [("izvinit", "imp.pl")]
"""Was der NPC sagt, wenn er nicht versteht — «Извини́те?»"""


def _line(course: Course, refs: list[TokenRef]) -> dict:
    return {
        "text": " ".join(course.form(ref).text for ref in refs),
        "translit": " ".join(course.form(ref).translit for ref in refs),
        "audio_text": spoken_text(course, refs),
    }


def village_payload(village: Village) -> dict:
    return {
        "places": [
            {
                "id": place.id,
                "name_ru": place.name_ru,
                "name_de": place.name_de,
                "kind": place.kind,
                "art": place.art,
                "hotspot": {
                    "x": place.hotspot.x, "y": place.hotspot.y,
                    "w": place.hotspot.w, "h": place.hotspot.h,
                },
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
    npc = village.npcs[scene.npc]
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
    turn = turns[index]
    exercise = scenes.turn_exercise(scene, seed, index, turn)
    return {
        "index": index,
        "turn_count": len(turns),
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
    turn = turns[index]
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && .venv/bin/pytest tests/test_game_service.py -q -p no:cacheprovider`
Expected: PASS (9 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/game/service.py backend/tests/test_game_service.py
git commit -m "feat(game): grade scene turns and feed them to the review schedule"
```

---

### Task 5: Bilder — Auflösung, Route und die gezeichneten SVG

**Files:**
- Create: `backend/app/game/art.py`
- Create: `backend/tests/test_game_art.py`
- Create: `content/game/art/village.svg`
- Create: `content/game/art/shkola.svg`
- Create: `content/game/art/kafe.svg`
- Create: `content/game/art/magazin.svg`
- Create: `content/game/art/bar.svg`
- Create: `content/game/art/npc_pjotr.svg`
- Create: `content/game/art/npc_nina.svg`
- Modify: `backend/app/game/validator.py` (Regel 8)
- Modify: `backend/tests/test_village_validator.py`

**Interfaces:**
- Produces: `art.art_path(art_dir: Path, art_id: str) -> Path | None`, `art.MEDIA_TYPES: dict[str, str]`
- Ändert: `validate_village(course, village, art_dir: Path | None = None) -> list[str]`

- [ ] **Step 1: Write the failing test**

`backend/tests/test_game_art.py`:

```python
from app.game import art


def test_finds_the_svg(tmp_path):
    (tmp_path / "bar.svg").write_text("<svg/>", encoding="utf-8")
    assert art.art_path(tmp_path, "bar").name == "bar.svg"


def test_a_raster_image_wins_over_the_svg(tmp_path):
    (tmp_path / "bar.svg").write_text("<svg/>", encoding="utf-8")
    (tmp_path / "bar.webp").write_bytes(b"fake")
    assert art.art_path(tmp_path, "bar").name == "bar.webp"


def test_png_wins_over_svg_but_loses_to_webp(tmp_path):
    (tmp_path / "bar.svg").write_text("<svg/>", encoding="utf-8")
    (tmp_path / "bar.png").write_bytes(b"fake")
    assert art.art_path(tmp_path, "bar").name == "bar.png"
    (tmp_path / "bar.webp").write_bytes(b"fake")
    assert art.art_path(tmp_path, "bar").name == "bar.webp"


def test_returns_none_when_nothing_is_there(tmp_path):
    assert art.art_path(tmp_path, "bar") is None


def test_rejects_ids_that_could_escape_the_directory(tmp_path):
    (tmp_path / "bar.svg").write_text("<svg/>", encoding="utf-8")
    for evil in ("../bar", "a/b", "bar.svg", "..", "Bar"):
        assert art.art_path(tmp_path, evil) is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && .venv/bin/pytest tests/test_game_art.py -q -p no:cacheprovider`
Expected: FAIL with `ImportError: cannot import name 'art' from 'app.game'`

- [ ] **Step 3: Write the art resolution**

`backend/app/game/art.py`:

```python
import re
from pathlib import Path

SUFFIXES = (".webp", ".png", ".svg")
"""Suchreihenfolge: ein extern erzeugtes Rasterbild schlägt die gezeichnete SVG."""

MEDIA_TYPES = {".webp": "image/webp", ".png": "image/png", ".svg": "image/svg+xml"}

_SAFE_ID = re.compile(r"[a-z0-9_]+")


def art_path(art_dir: Path, art_id: str) -> Path | None:
    """Die Bilddatei zu einer Id, oder None.

    Die Id kommt aus einer URL. Sie muss deshalb streng geprueft werden, sonst
    liesse sich ueber `../` aus dem Bildverzeichnis herauslesen.
    """
    if not _SAFE_ID.fullmatch(art_id):
        return None
    for suffix in SUFFIXES:
        candidate = art_dir / f"{art_id}{suffix}"
        if candidate.is_file():
            return candidate
    return None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && .venv/bin/pytest tests/test_game_art.py -q -p no:cacheprovider`
Expected: PASS (5 tests)

- [ ] **Step 5: Draw the SVG**

Sieben Dateien unter `content/game/art/`. Anforderungen:

- `village.svg` — `viewBox="0 0 1600 900"` (16:9). Vier Gebäude, deren sichtbare Umrisse mit den Klickflächen aus `content/game/places.json` zusammenfallen: шко́ла bei x 0.08–0.26, кафе́ bei 0.30–0.48, магази́н bei 0.52–0.70, бар bei 0.74–0.92, jeweils y 0.30–0.64. Über jedem Gebäude ein Schild mit dem **russischen** Namen samt Betonungszeichen. Dorfstraße im Vordergrund, Hügel und Wald im Hintergrund.
- `shkola.svg`, `kafe.svg`, `magazin.svg`, `bar.svg` — `viewBox="0 0 1200 800"` (3:2), Innenansicht des jeweiligen Ortes.
- `npc_pjotr.svg`, `npc_nina.svg` — `viewBox="0 0 400 400"` (1:1), Brustbild.

Farben aus der bestehenden Oberfläche aufnehmen: Slate für Umrisse, Sky für Akzente, warme Erdtöne für Holz und Dächer. Keine eingebetteten Rasterbilder, keine externen Schriften — die SVG müssen ohne Netz funktionieren.

Gerüst für `village.svg`, an dem sich die übrigen drei Gebäude orientieren. Die Zahlen sind die Klickflächen aus `places.json` mal 1600 beziehungsweise 900:

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1600 900" role="img">
  <rect width="1600" height="900" fill="#e0f2fe"/>
  <path d="M0 470 Q 400 380 800 450 T 1600 430 V900 H0 Z" fill="#86efac"/>
  <path d="M0 640 Q 800 600 1600 660 V900 H0 Z" fill="#d6d3d1"/>

  <!-- шко́ла: hotspot x .08-.26, y .30-.60  ->  128-416, 270-540 -->
  <g>
    <rect x="128" y="330" width="288" height="210" rx="8" fill="#fef3c7" stroke="#78716c" stroke-width="6"/>
    <path d="M112 330 L272 250 L432 330 Z" fill="#b45309" stroke="#78716c" stroke-width="6"/>
    <rect x="240" y="430" width="64" height="110" fill="#78716c"/>
    <rect x="160" y="370" width="60" height="50" fill="#bae6fd" stroke="#78716c" stroke-width="4"/>
    <rect x="324" y="370" width="60" height="50" fill="#bae6fd" stroke="#78716c" stroke-width="4"/>
    <rect x="176" y="286" width="192" height="40" rx="6" fill="#0369a1"/>
    <text x="272" y="314" text-anchor="middle" font-family="system-ui, sans-serif"
          font-size="26" fill="#ffffff">шко́ла</text>
  </g>

  <!-- кафе́ 480-768, магази́н 832-1120, бар 1184-1472: gleiches Muster,
       je eigenes Dach, eigene Farbe, eigenes Schild -->
</svg>
```

Das Schild trägt den russischen Namen mit Betonungszeichen und benutzt `system-ui` — keine geladene Schrift. `role="img"` sorgt dafür, dass Vorleseprogramme das `alt` der einbettenden Seite benutzen.

- [ ] **Step 6: Add the art rule to the validator**

In `backend/app/game/validator.py` die Signatur ändern und die Regel ergänzen:

```python
from pathlib import Path

from app.game.art import art_path


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
```

`art_dir=None` heißt: Bilder nicht prüfen. Die Tests aus Task 2 schreiben ihr Dorf nach `tmp_path` und haben dort keine Bilder — sie rufen weiterhin ohne `art_dir` auf und bleiben grün.

In `backend/scripts/validate_content.py` den Aufruf erweitern:

```python
    errors = validate_course(course) + validate_village(course, village, game_dir / "art")
```

- [ ] **Step 7: Add the art rule test**

Ans Ende von `backend/tests/test_village_validator.py`:

```python
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
```

- [ ] **Step 8: Run the whole check**

Run: `cd backend && .venv/bin/pytest tests/test_village_validator.py tests/test_game_art.py -q -p no:cacheprovider && cd .. && make validate`
Expected: Tests PASS, `make validate` meldet OK mit 4 Orten und 2 Szenen

- [ ] **Step 9: Commit**

```bash
git add backend/app/game/art.py backend/app/game/validator.py backend/scripts/validate_content.py backend/tests/test_game_art.py backend/tests/test_village_validator.py content/game/art
git commit -m "feat(game): draw the village and resolve raster images over svg"
```

---

### Task 6: API-Routen

**Files:**
- Modify: `backend/app/dependencies.py`
- Modify: `backend/app/api/routes.py`
- Modify: `backend/app/config.py`
- Create: `backend/tests/test_game_routes.py`

**Interfaces:**
- Consumes: alles aus Task 3 bis 5
- Produces: `dependencies.get_village() -> Village`; die sechs Routen unter `/api/game`

- [ ] **Step 1: Write the failing test**

`backend/tests/test_game_routes.py`:

```python
def test_village_route_lists_the_places(client):
    response = client.get("/api/game/village")
    assert response.status_code == 200
    assert {place["id"] for place in response.json()["places"]} >= {"bar", "magazin", "shkola"}


def test_place_route_returns_its_people(client):
    response = client.get("/api/game/places/bar")
    assert response.status_code == 200
    assert response.json()["kind"] == "npcs"


def test_unknown_place_is_a_404(client):
    assert client.get("/api/game/places/nirgendwo").status_code == 404


def test_starting_a_scene_returns_a_seed(client):
    response = client.post("/api/game/places/bar/scene", json={})
    assert response.status_code == 200
    body = response.json()
    assert body["seed"]
    assert body["turn_count"] >= 2


def test_a_turn_hides_the_solution(client):
    started = client.post("/api/game/places/bar/scene", json={}).json()
    response = client.get(
        f"/api/game/scenes/{started['scene_id']}/turns/0", params={"seed": started["seed"]}
    )
    assert response.status_code == 200
    body = response.json()
    assert "solution" not in body["exercise"]
    assert body["npc_line"]["text"]


def test_a_turn_beyond_the_end_is_a_404(client):
    started = client.post("/api/game/places/bar/scene", json={}).json()
    response = client.get(
        f"/api/game/scenes/{started['scene_id']}/turns/99", params={"seed": started["seed"]}
    )
    assert response.status_code == 404


def test_answering_a_turn_grades_it(client):
    started = client.post("/api/game/places/bar/scene", json={}).json()
    response = client.post(
        f"/api/game/scenes/{started['scene_id']}/turns/0",
        json={"seed": started["seed"], "submission": {"tile_indices": []}},
    )
    assert response.status_code == 200
    assert response.json()["correct"] is False
    assert response.json()["npc_reaction"]["text"]


def test_art_route_serves_the_village_map(client):
    response = client.get("/api/game/art/village")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("image/svg+xml")


def test_art_route_refuses_to_escape_the_directory(client):
    assert client.get("/api/game/art/..%2F..%2Fetc%2Fpasswd").status_code == 404
```

`client` ist die vorhandene Fixture aus `backend/tests/conftest.py`. Prüfe dort nach, ob sie das echte `content/`-Verzeichnis benutzt; falls sie auf ein temporäres zeigt, muss sie zusätzlich `game_dir` auf `content/game` setzen.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && .venv/bin/pytest tests/test_game_routes.py -q -p no:cacheprovider`
Expected: FAIL mit 404 auf allen Routen

- [ ] **Step 3: Add the setting and the dependency**

In `backend/app/config.py`, in `Settings` nach `content_dir`:

```python
    game_dir: str = os.environ.get(
        "GAME_DIR", str(Path(__file__).resolve().parents[2] / "content" / "game")
    )
```

In `backend/app/dependencies.py` ergänzen:

```python
from app.game.loader import load_village
from app.game.models import Village


@lru_cache(maxsize=1)
def _load_village() -> Village:
    return load_village(settings.game_dir)


def get_village() -> Village:
    """Das Dorf, einmal je Prozess geladen."""
    return _load_village()
```

- [ ] **Step 4: Add the routes**

In `backend/app/api/routes.py` die Importe ergänzen:

```python
import datetime as dt
from pathlib import Path

from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.dependencies import get_village
from app.game import art as game_art
from app.game import service as game_service
from app.game.models import Village
```

Ans Ende der Datei:

```python
class SceneStartRequest(BaseModel):
    npc_id: str | None = None


class TurnAnswerRequest(BaseModel):
    seed: str
    submission: dict


@router.get("/game/village")
def read_village(village: Village = Depends(get_village)) -> dict:
    return game_service.village_payload(village)


@router.get("/game/places/{place_id}")
def read_place(
    place_id: str,
    conn: Connection = Depends(get_db),
    course: Course = Depends(get_course),
    village: Village = Depends(get_village),
) -> dict:
    if place_id not in village.places:
        raise HTTPException(status_code=404, detail=f"Ort {place_id} gibt es nicht")
    return game_service.place_payload(village, course, conn, place_id)


@router.post("/game/places/{place_id}/scene")
def start_scene(
    place_id: str,
    payload: SceneStartRequest,
    conn: Connection = Depends(get_db),
    course: Course = Depends(get_course),
    village: Village = Depends(get_village),
) -> dict:
    if place_id not in village.places:
        raise HTTPException(status_code=404, detail=f"Ort {place_id} gibt es nicht")
    try:
        return game_service.start_scene(
            village, course, conn,
            place_id=place_id, npc_id=payload.npc_id,
            now=dt.datetime.now().isoformat(timespec="seconds"),
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/game/scenes/{scene_id}/turns/{index}")
def read_turn(
    scene_id: str,
    index: int,
    seed: str,
    course: Course = Depends(get_course),
    village: Village = Depends(get_village),
) -> dict:
    if scene_id not in village.scenes:
        raise HTTPException(status_code=404, detail=f"Szene {scene_id} gibt es nicht")
    try:
        return game_service.turn_payload(
            course, village, scene_id=scene_id, seed=seed, index=index
        )
    except IndexError as exc:
        raise HTTPException(status_code=404, detail=f"Zug {index} gibt es nicht") from exc


@router.post("/game/scenes/{scene_id}/turns/{index}")
def answer_turn(
    scene_id: str,
    index: int,
    payload: TurnAnswerRequest,
    conn: Connection = Depends(get_db),
    course: Course = Depends(get_course),
    village: Village = Depends(get_village),
) -> dict:
    if scene_id not in village.scenes:
        raise HTTPException(status_code=404, detail=f"Szene {scene_id} gibt es nicht")
    now = dt.datetime.now()
    try:
        return game_service.answer_turn(
            conn, course, village,
            scene_id=scene_id, seed=payload.seed, index=index,
            submission=payload.submission,
            today=now.date().isoformat(), now=now.isoformat(timespec="seconds"),
        )
    except IndexError as exc:
        raise HTTPException(status_code=404, detail=f"Zug {index} gibt es nicht") from exc


@router.get("/game/art/{art_id}")
def read_art(art_id: str) -> FileResponse:
    path = game_art.art_path(Path(settings.game_dir) / "art", art_id)
    if path is None:
        raise HTTPException(status_code=404, detail=f"Bild {art_id} gibt es nicht")
    return FileResponse(path, media_type=game_art.MEDIA_TYPES[path.suffix])
```

Falls `settings` in `routes.py` noch nicht importiert ist: `from app.config import settings`.

- [ ] **Step 5: Run test to verify it passes**

Run: `cd backend && .venv/bin/pytest tests/test_game_routes.py -q -p no:cacheprovider`
Expected: PASS (9 tests)

- [ ] **Step 6: Run the whole backend suite**

Run: `cd backend && .venv/bin/pytest -q -p no:cacheprovider`
Expected: alle Tests grün

- [ ] **Step 7: Commit**

```bash
git add backend/app/api/routes.py backend/app/dependencies.py backend/app/config.py backend/tests/test_game_routes.py
git commit -m "feat(game): expose the village over the api"
```

---

### Task 7: Frontend-Grundlage und volle Breite

**Files:**
- Create: `frontend/src/gameTypes.ts`
- Create: `frontend/src/gameApi.ts`
- Modify: `frontend/src/App.tsx`
- Create: `frontend/src/App.width.test.tsx`

**Interfaces:**
- Produces: Typen `Place`, `VillageOverview`, `PlaceDetail`, `SceneStart`, `TurnView`, `TurnResult`; Funktionen `getVillage`, `getPlace`, `startScene`, `getTurn`, `answerTurn`, `artUrl`

- [ ] **Step 1: Write the failing test**

`frontend/src/App.width.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import * as api from "./courseApi";
import * as gameApi from "./gameApi";
import App from "./App";

function renderAt(path: string) {
  vi.spyOn(api, "getCourse").mockResolvedValue({ stages: [] });
  vi.spyOn(gameApi, "getVillage").mockResolvedValue({ places: [] });
  return render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>,
  );
}

describe("Seitenbreite", () => {
  it("hält Kurs und Profil schmal", () => {
    renderAt("/kurs");
    expect(screen.getByRole("main")).toHaveClass("max-w-3xl");
  });

  it("gibt dem Dorf die volle Breite", () => {
    renderAt("/dorf");
    expect(screen.getByRole("main")).not.toHaveClass("max-w-3xl");
  });
});
```

`App.tsx` rendert bislang seinen eigenen `MemoryRouter` nicht — prüfe, ob `App` einen Router mitbringt. Falls ja, entferne den `MemoryRouter` aus dem Test und benutze stattdessen `window.history.pushState({}, "", path)` vor dem Rendern.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/App.width.test.tsx`
Expected: FAIL — `gameApi` existiert nicht

- [ ] **Step 3: Write the types**

`frontend/src/gameTypes.ts`:

```ts
import type { BuildSentenceExercise, Submission } from "./courseTypes";

export interface Hotspot {
  x: number;
  y: number;
  w: number;
  h: number;
}

export interface Place {
  id: string;
  name_ru: string;
  name_de: string;
  kind: "course" | "npcs" | "shopping";
  art: string;
  hotspot: Hotspot;
}

export interface VillageOverview {
  places: Place[];
}

export interface Npc {
  id: string;
  name_ru: string;
  name_de: string;
  about_de: string;
  art: string;
}

export interface PlaceDetail {
  id: string;
  name_ru: string;
  name_de: string;
  kind: Place["kind"];
  art: string;
  npcs: Npc[];
  next_unit_id?: number | null;
}

export interface SceneStart {
  scene_id: string;
  seed: string;
  title_de: string;
  intro_de: string;
  hint_unit: number;
  npc: { id: string; name_ru: string; name_de: string; art: string };
  turn_count: number;
}

export interface SpokenLine {
  text: string;
  translit: string;
  audio_text: string;
}

export interface TurnView {
  index: number;
  turn_count: number;
  npc_line: SpokenLine;
  exercise: BuildSentenceExercise;
}

export interface TurnResult {
  correct: boolean;
  solution_text: string;
  solution_translit: string;
  solution_audio: string[];
  explanation_de: string;
  npc_reaction: SpokenLine | null;
  scene_completed: boolean;
  outro_de: string;
}

export type { Submission };
```

- [ ] **Step 4: Write the api module**

`frontend/src/gameApi.ts` — dem Muster von `courseApi.ts` folgen (dort nachsehen, wie die Basis-URL bestimmt und wie `fetch` gekapselt wird, und dieselbe Hilfsfunktion benutzen):

```ts
import type {
  PlaceDetail,
  SceneStart,
  Submission,
  TurnResult,
  TurnView,
  VillageOverview,
} from "./gameTypes";

const BASE = import.meta.env.VITE_API_URL ?? "";

async function json<T>(input: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE}${input}`, init);
  if (!response.ok) throw new Error(`${response.status} ${input}`);
  return (await response.json()) as T;
}

function post<T>(path: string, body: unknown): Promise<T> {
  return json<T>(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export function artUrl(artId: string): string {
  return `${BASE}/api/game/art/${artId}`;
}

export function getVillage(): Promise<VillageOverview> {
  return json("/api/game/village");
}

export function getPlace(placeId: string): Promise<PlaceDetail> {
  return json(`/api/game/places/${placeId}`);
}

export function startScene(placeId: string, npcId?: string): Promise<SceneStart> {
  return post(`/api/game/places/${placeId}/scene`, { npc_id: npcId ?? null });
}

export function getTurn(sceneId: string, seed: string, index: number): Promise<TurnView> {
  const query = new URLSearchParams({ seed });
  return json(`/api/game/scenes/${sceneId}/turns/${index}?${query}`);
}

export function answerTurn(
  sceneId: string,
  index: number,
  seed: string,
  submission: Submission,
): Promise<TurnResult> {
  return post(`/api/game/scenes/${sceneId}/turns/${index}`, { seed, submission });
}
```

Weicht `courseApi.ts` bei der Basis-URL ab, gilt dessen Variante — nicht zwei Wege im selben Projekt.

- [ ] **Step 5: Make the width depend on the route**

In `frontend/src/App.tsx`: `useLocation` importieren, den Reiter ergänzen und `main` bedingt setzen.

```tsx
import { NavLink, Route, Routes, useLocation } from "react-router-dom";
```

```tsx
const TABS = [
  { to: "/kurs", label: "Kurs" },
  { to: "/dorf", label: "Dorf" },
  { to: "/wiederholen", label: "Wiederholen" },
  { to: "/profil", label: "Profil" },
];

const WIDE_PREFIX = "/dorf";
```

Im Rumpf, vor dem `return`:

```tsx
  const { pathname } = useLocation();
  // Das Dorf ist eine Karte und braucht Platz. Fliesstext bleibt schmal:
  // ueber die volle Breite gezogen liest er sich schlechter, nicht besser.
  const wide = pathname.startsWith(WIDE_PREFIX);
```

und das `main`-Element:

```tsx
          <main className={wide ? "px-4 py-6" : "mx-auto max-w-3xl px-4 py-6"}>
```

Die Kopfzeile behält ihr `max-w-3xl` nicht — auch sie soll im Dorf mitwachsen:

```tsx
            <div
              className={
                wide
                  ? "flex items-center gap-6 px-4 py-3"
                  : "mx-auto flex max-w-3xl items-center gap-6 px-4 py-3"
              }
            >
```

- [ ] **Step 6: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/App.width.test.tsx && npx tsc --noEmit -p tsconfig.json`
Expected: PASS, Typprüfung ohne Fehler

- [ ] **Step 7: Commit**

```bash
git add frontend/src/gameTypes.ts frontend/src/gameApi.ts frontend/src/App.tsx frontend/src/App.width.test.tsx
git commit -m "feat(game): add the village tab and let it use the full width"
```

---

### Task 8: Dorfkarte

**Files:**
- Create: `frontend/src/views/VillageView.tsx`
- Create: `frontend/src/views/VillageView.test.tsx`
- Modify: `frontend/src/App.tsx` (Route)

**Interfaces:**
- Consumes: `getVillage`, `artUrl`, Typ `Place`
- Produces: Route `/dorf`

- [ ] **Step 1: Write the failing test**

`frontend/src/views/VillageView.test.tsx`:

```tsx
import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as api from "../gameApi";
import VillageView from "./VillageView";

const village = {
  places: [
    {
      id: "bar",
      name_ru: "бар",
      name_de: "Bar",
      kind: "npcs" as const,
      art: "bar",
      hotspot: { x: 0.1, y: 0.5, w: 0.2, h: 0.25 },
    },
  ],
};

function renderVillage() {
  return render(
    <MemoryRouter initialEntries={["/dorf"]}>
      <Routes>
        <Route path="/dorf" element={<VillageView />} />
        <Route path="/dorf/:placeId" element={<p>Ort geöffnet</p>} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("VillageView", () => {
  beforeEach(() => vi.restoreAllMocks());

  it("zeigt die Karte", async () => {
    vi.spyOn(api, "getVillage").mockResolvedValue(village);
    renderVillage();
    expect(await screen.findByAltText("Das Dorf")).toBeInTheDocument();
  });

  it("setzt die Klickfläche auf die Anteile aus dem Inhalt", async () => {
    vi.spyOn(api, "getVillage").mockResolvedValue(village);
    renderVillage();
    const button = await screen.findByRole("button", { name: /бар/ });
    expect(button.style.left).toBe("10%");
    expect(button.style.top).toBe("50%");
    expect(button.style.width).toBe("20%");
    expect(button.style.height).toBe("25%");
  });

  it("öffnet den Ort beim Klick", async () => {
    vi.spyOn(api, "getVillage").mockResolvedValue(village);
    renderVillage();
    fireEvent.click(await screen.findByRole("button", { name: /бар/ }));
    expect(await screen.findByText("Ort geöffnet")).toBeInTheDocument();
  });

  it("meldet einen Ladefehler statt leer zu bleiben", async () => {
    vi.spyOn(api, "getVillage").mockRejectedValue(new Error("kaputt"));
    renderVillage();
    expect(await screen.findByText(/konnte nicht geladen/)).toBeInTheDocument();
  });

  it("bleibt bedienbar, wenn die Karte fehlt", async () => {
    vi.spyOn(api, "getVillage").mockResolvedValue(village);
    renderVillage();
    const map = await screen.findByAltText("Das Dorf");
    fireEvent.error(map);
    // Ohne Bild braucht die Klickfläche einen sichtbaren Namen, sonst ist der
    // Ort nicht mehr zu finden — Abschnitt 6 der Spec.
    expect(await screen.findByRole("button", { name: /бар/ })).toBeVisible();
    expect(screen.getByTestId("village-map")).toHaveClass("bg-slate-200");
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/views/VillageView.test.tsx`
Expected: FAIL — `VillageView` existiert nicht

- [ ] **Step 3: Write the view**

`frontend/src/views/VillageView.tsx`:

```tsx
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { artUrl, getVillage } from "../gameApi";
import type { Place } from "../gameTypes";

export default function VillageView() {
  const navigate = useNavigate();
  const [places, setPlaces] = useState<Place[] | null>(null);
  const [error, setError] = useState(false);
  const [mapMissing, setMapMissing] = useState(false);

  useEffect(() => {
    getVillage()
      .then((village) => setPlaces(village.places))
      .catch(() => setError(true));
  }, []);

  if (error) return <p>Das Dorf konnte nicht geladen werden.</p>;
  if (!places) return <p>Das Dorf wird geladen …</p>;

  return (
    <section className="space-y-4">
      <h2 className="text-2xl font-semibold">Дере́вня — dein Dorf</h2>
      {/* Die Karte gibt das Seitenverhaeltnis vor; die Klickflaechen sind
          Anteile davon und sitzen deshalb bei jeder Fenstergroesse richtig.
          Fehlt das Bild, traegt der Kasten selbst das Verhaeltnis und die
          Flaechen bekommen sichtbare Beschriftung — das Dorf bleibt begehbar. */}
      <div
        data-testid="village-map"
        className={`relative mx-auto aspect-[16/9] w-full max-w-[1600px] overflow-hidden rounded-2xl ${
          mapMissing ? "bg-slate-200" : ""
        }`}
      >
        {!mapMissing && (
          <img
            src={artUrl("village")}
            alt="Das Dorf"
            onError={() => setMapMissing(true)}
            className="block h-full w-full object-cover"
          />
        )}
        {places.map((place) => (
          <button
            key={place.id}
            type="button"
            onClick={() => navigate(`/dorf/${place.id}`)}
            title={place.name_de}
            style={{
              left: `${place.hotspot.x * 100}%`,
              top: `${place.hotspot.y * 100}%`,
              width: `${place.hotspot.w * 100}%`,
              height: `${place.hotspot.h * 100}%`,
            }}
            className="absolute flex items-center justify-center rounded-xl border-2 border-transparent transition hover:border-sky-500 hover:bg-sky-500/10 focus:border-sky-600 focus:outline-none"
          >
            {mapMissing ? (
              <span className="rounded-lg bg-white/90 px-2 py-1 text-sm font-medium">
                {place.name_ru}
              </span>
            ) : (
              <span className="sr-only">
                {place.name_ru} — {place.name_de}
              </span>
            )}
          </button>
        ))}
      </div>
      <ul className="flex flex-wrap gap-3 text-sm text-slate-600">
        {places.map((place) => (
          <li key={place.id}>
            <span className="font-medium text-slate-900">{place.name_ru}</span> {place.name_de}
          </li>
        ))}
      </ul>
    </section>
  );
}
```

- [ ] **Step 4: Add the routes**

In `frontend/src/App.tsx` importieren und eintragen:

```tsx
import VillageView from "./views/VillageView";
import PlaceView from "./views/PlaceView";
import SceneView from "./views/SceneView";
```

```tsx
              <Route path="/dorf" element={<VillageView />} />
              <Route path="/dorf/:placeId" element={<PlaceView />} />
              <Route path="/dorf/:placeId/szene/:sceneId" element={<SceneView />} />
```

`PlaceView` und `SceneView` entstehen in Task 9 und 10. Damit dieser Task für sich lauffähig bleibt, lege beide jetzt als Stummel an:

`frontend/src/views/PlaceView.tsx`:

```tsx
export default function PlaceView() {
  return <p>Ort wird geladen …</p>;
}
```

`frontend/src/views/SceneView.tsx`:

```tsx
export default function SceneView() {
  return <p>Szene wird geladen …</p>;
}
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/views/VillageView.test.tsx && npx tsc --noEmit -p tsconfig.json`
Expected: PASS (4 Tests), Typprüfung sauber

- [ ] **Step 6: Commit**

```bash
git add frontend/src/views/VillageView.tsx frontend/src/views/VillageView.test.tsx frontend/src/views/PlaceView.tsx frontend/src/views/SceneView.tsx frontend/src/App.tsx
git commit -m "feat(game): show the village map with clickable buildings"
```

---

### Task 9: Ortsansicht

**Files:**
- Modify: `frontend/src/views/PlaceView.tsx`
- Create: `frontend/src/views/PlaceView.test.tsx`

**Interfaces:**
- Consumes: `getPlace`, `startScene`, `artUrl`, Typ `PlaceDetail`
- Produces: navigiert nach `/dorf/:placeId/szene/:sceneId?seed=…`

- [ ] **Step 1: Write the failing test**

`frontend/src/views/PlaceView.test.tsx`:

```tsx
import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as api from "../gameApi";
import PlaceView from "./PlaceView";

const bar = {
  id: "bar",
  name_ru: "бар",
  name_de: "Bar",
  kind: "npcs" as const,
  art: "bar",
  npcs: [
    {
      id: "pjotr",
      name_ru: "Пётр",
      name_de: "Pjotr",
      about_de: "Sitzt jeden Abend am selben Platz.",
      art: "npc_pjotr",
    },
  ],
};

const started = {
  scene_id: "bar-01",
  seed: "bar-01:2026-09-08T10:00:00",
  title_de: "Der Mann am Tresen",
  intro_de: "Ein älterer Mann dreht sich zu dir um.",
  hint_unit: 15,
  npc: { id: "pjotr", name_ru: "Пётр", name_de: "Pjotr", art: "npc_pjotr" },
  turn_count: 2,
};

function renderPlace(path = "/dorf/bar") {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/dorf/:placeId" element={<PlaceView />} />
        <Route path="/dorf/:placeId/szene/:sceneId" element={<p>Szene läuft</p>} />
        <Route path="/kurs/:unitId" element={<p>Einheit läuft</p>} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("PlaceView", () => {
  beforeEach(() => vi.restoreAllMocks());

  it("stellt die Leute des Ortes vor", async () => {
    vi.spyOn(api, "getPlace").mockResolvedValue(bar);
    renderPlace();
    expect(await screen.findByText("Пётр")).toBeInTheDocument();
    expect(screen.getByText(/Sitzt jeden Abend/)).toBeInTheDocument();
  });

  it("startet beim Anklicken einer Person eine Szene", async () => {
    vi.spyOn(api, "getPlace").mockResolvedValue(bar);
    const start = vi.spyOn(api, "startScene").mockResolvedValue(started);
    renderPlace();
    fireEvent.click(await screen.findByRole("button", { name: /Пётр/ }));
    expect(await screen.findByText("Szene läuft")).toBeInTheDocument();
    expect(start).toHaveBeenCalledWith("bar", "pjotr");
  });

  it("startet beim Laden direkt eine Szene, wenn der Ort ein Laden ist", async () => {
    vi.spyOn(api, "getPlace").mockResolvedValue({ ...bar, kind: "shopping", npcs: [] });
    const start = vi.spyOn(api, "startScene").mockResolvedValue(started);
    renderPlace();
    fireEvent.click(await screen.findByRole("button", { name: /Einkaufen/ }));
    expect(start).toHaveBeenCalledWith("bar", undefined);
  });

  it("führt beim Sprachkurs in die nächste offene Einheit", async () => {
    vi.spyOn(api, "getPlace").mockResolvedValue({
      ...bar,
      kind: "course",
      npcs: [],
      next_unit_id: 7,
    });
    renderPlace();
    fireEvent.click(await screen.findByRole("button", { name: /Einheit 7/ }));
    expect(await screen.findByText("Einheit läuft")).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/views/PlaceView.test.tsx`
Expected: FAIL — der Stummel zeigt nur „Ort wird geladen …"

- [ ] **Step 3: Write the view**

`frontend/src/views/PlaceView.tsx` vollständig ersetzen:

```tsx
import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { artUrl, getPlace, startScene } from "../gameApi";
import type { PlaceDetail } from "../gameTypes";

export default function PlaceView() {
  const { placeId } = useParams();
  const navigate = useNavigate();
  const [place, setPlace] = useState<PlaceDetail | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    if (!placeId) return;
    getPlace(placeId)
      .then(setPlace)
      .catch(() => setError(true));
  }, [placeId]);

  const open = (npcId?: string) => {
    if (!placeId) return;
    startScene(placeId, npcId)
      .then((scene) =>
        navigate(
          `/dorf/${placeId}/szene/${scene.scene_id}?seed=${encodeURIComponent(scene.seed)}`,
        ),
      )
      .catch(() => setError(true));
  };

  if (error) return <p>Der Ort konnte nicht geladen werden.</p>;
  if (!place) return <p>Ort wird geladen …</p>;

  return (
    <section className="mx-auto max-w-5xl space-y-6">
      <header className="space-y-1">
        <h2 className="text-2xl font-semibold">{place.name_ru}</h2>
        <p className="text-slate-600">{place.name_de}</p>
      </header>

      <img
        src={artUrl(place.art)}
        alt={place.name_de}
        className="block w-full rounded-2xl"
      />

      {place.kind === "course" && (
        <button
          type="button"
          disabled={!place.next_unit_id}
          onClick={() => navigate(`/kurs/${place.next_unit_id}`)}
          className="rounded-xl bg-sky-600 px-5 py-2 font-medium text-white disabled:bg-slate-300"
        >
          {place.next_unit_id ? `Einheit ${place.next_unit_id} beginnen` : "Alles geschafft"}
        </button>
      )}

      {place.kind === "shopping" && (
        <button
          type="button"
          onClick={() => open(undefined)}
          className="rounded-xl bg-sky-600 px-5 py-2 font-medium text-white"
        >
          Einkaufen gehen
        </button>
      )}

      {place.kind === "npcs" && (
        <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {place.npcs.map((npc) => (
            <li key={npc.id}>
              <button
                type="button"
                onClick={() => open(npc.id)}
                className="flex w-full items-center gap-3 rounded-2xl border-2 border-slate-200 p-3 text-left hover:border-sky-400"
              >
                <img src={artUrl(npc.art)} alt="" className="h-16 w-16 rounded-full" />
                <span>
                  <span className="block font-medium">{npc.name_ru}</span>
                  <span className="block text-sm text-slate-600">{npc.about_de}</span>
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}

      <button
        type="button"
        onClick={() => navigate("/dorf")}
        className="text-sky-700 underline"
      >
        Zurück ins Dorf
      </button>
    </section>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/views/PlaceView.test.tsx && npx tsc --noEmit -p tsconfig.json`
Expected: PASS (4 Tests)

- [ ] **Step 5: Commit**

```bash
git add frontend/src/views/PlaceView.tsx frontend/src/views/PlaceView.test.tsx
git commit -m "feat(game): open a place and start a scene from it"
```

---

### Task 10: Gesprächsansicht

**Files:**
- Modify: `frontend/src/views/SceneView.tsx`
- Create: `frontend/src/views/SceneView.test.tsx`
- Create: `frontend/src/game/NpcLine.tsx`

**Interfaces:**
- Consumes: `getTurn`, `answerTurn`, `artUrl`, `course/BuildSentenceExercise`, `audio/SpeakerButton`
- Produces: nichts, was spätere Tasks brauchen

Kern dieses Tasks ist die Fehlerbehandlung aus Abschnitt 6 der Spec: nach einer falschen Antwort wird **derselbe Zug sofort genau einmal** wiederholt, danach geht es unabhängig vom Ausgang weiter.

- [ ] **Step 1: Write the failing test**

`frontend/src/views/SceneView.test.tsx`:

```tsx
import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as api from "../gameApi";
import SceneView from "./SceneView";

const turn = (index: number) => ({
  index,
  turn_count: 2,
  npc_line: { text: "приве́т как дела́", translit: "privét kak delá", audio_text: "приве́т" },
  exercise: {
    id: `bar-01:s1#${index}`,
    type: "build_sentence" as const,
    prompt_de: "Sag, dass es dir gut geht.",
    audio_prompt: false,
    tiles: [
      { index: 0, text: "хорошо́", translit: "chorošó" },
      { index: 1, text: "пло́хо", translit: "plócho" },
    ],
  },
});

const wrong = {
  correct: false,
  solution_text: "хорошо́",
  solution_translit: "chorošó",
  solution_audio: ["хорошо́"],
  explanation_de: "Richtig ist: хорошо́",
  npc_reaction: { text: "извини́те", translit: "izviníte", audio_text: "извини́те" },
  scene_completed: false,
  outro_de: "",
};

const right = { ...wrong, correct: true, explanation_de: "", npc_reaction: null };

function renderScene() {
  return render(
    <MemoryRouter initialEntries={["/dorf/bar/szene/bar-01?seed=s1"]}>
      <Routes>
        <Route path="/dorf/:placeId/szene/:sceneId" element={<SceneView />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("SceneView", () => {
  beforeEach(() => vi.restoreAllMocks());

  it("zeigt die Zeile des NPC und die Kacheln", async () => {
    vi.spyOn(api, "getTurn").mockResolvedValue(turn(0));
    renderScene();
    expect(await screen.findByText("приве́т как дела́")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /хорошо́/ })).toBeInTheDocument();
  });

  it("wiederholt den Zug nach einem Fehler genau einmal", async () => {
    const getTurn = vi.spyOn(api, "getTurn").mockResolvedValue(turn(0));
    vi.spyOn(api, "answerTurn").mockResolvedValue(wrong);
    renderScene();

    fireEvent.click(await screen.findByRole("button", { name: /хорошо́/ }));
    fireEvent.click(screen.getByRole("button", { name: "Prüfen" }));

    expect(await screen.findByText("извини́те")).toBeInTheDocument();
    expect(screen.getByText(/Richtig ist/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Nochmal" }));
    expect(getTurn).toHaveBeenCalledTimes(1);
    expect(screen.getByRole("button", { name: "Weiter" })).not.toBeUndefined();
  });

  it("geht nach dem zweiten Versuch weiter, auch wenn er falsch war", async () => {
    const getTurn = vi
      .spyOn(api, "getTurn")
      .mockResolvedValueOnce(turn(0))
      .mockResolvedValueOnce(turn(1));
    vi.spyOn(api, "answerTurn").mockResolvedValue(wrong);
    renderScene();

    fireEvent.click(await screen.findByRole("button", { name: /хорошо́/ }));
    fireEvent.click(screen.getByRole("button", { name: "Prüfen" }));
    fireEvent.click(await screen.findByRole("button", { name: "Nochmal" }));
    fireEvent.click(await screen.findByRole("button", { name: /хорошо́/ }));
    fireEvent.click(screen.getByRole("button", { name: "Prüfen" }));
    fireEvent.click(await screen.findByRole("button", { name: "Weiter" }));

    expect(getTurn).toHaveBeenCalledTimes(2);
  });

  it("zeigt am Ende das Nachwort", async () => {
    vi.spyOn(api, "getTurn").mockResolvedValue(turn(1));
    vi.spyOn(api, "answerTurn").mockResolvedValue({
      ...right,
      scene_completed: true,
      outro_de: "Pjotr nickt.",
    });
    renderScene();
    fireEvent.click(await screen.findByRole("button", { name: /хорошо́/ }));
    fireEvent.click(screen.getByRole("button", { name: "Prüfen" }));
    expect(await screen.findByText("Pjotr nickt.")).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/views/SceneView.test.tsx`
Expected: FAIL — der Stummel zeigt nur „Szene wird geladen …"

- [ ] **Step 3: Write the NPC line component**

`frontend/src/game/NpcLine.tsx`:

```tsx
import SpeakerButton from "../audio/SpeakerButton";
import RussianText from "../course/RussianText";
import type { SpokenLine } from "../gameTypes";

export default function NpcLine({ line, name }: { line: SpokenLine; name?: string }) {
  return (
    <div className="flex items-start gap-2 rounded-2xl bg-slate-100 p-3">
      <div className="flex-1">
        {name && <p className="text-sm font-medium text-slate-500">{name}</p>}
        <RussianText text={line.text} translit={line.translit} />
      </div>
      <SpeakerButton text={line.audio_text} />
    </div>
  );
}
```

Prüfe die Props von `RussianText` und `SpeakerButton` in `frontend/src/course/RussianText.tsx` und `frontend/src/audio/SpeakerButton.tsx` und passe die Aufrufe an — die dortigen Signaturen gelten, nicht die hier vermuteten.

- [ ] **Step 4: Write the scene view**

`frontend/src/views/SceneView.tsx` vollständig ersetzen:

```tsx
import { useCallback, useEffect, useState } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";

import BuildSentenceExercise from "../course/BuildSentenceExercise";
import NpcLine from "../game/NpcLine";
import { answerTurn, getTurn } from "../gameApi";
import type { Submission, TurnResult, TurnView } from "../gameTypes";

export default function SceneView() {
  const { placeId, sceneId } = useParams();
  const [params] = useSearchParams();
  const seed = params.get("seed") ?? "";
  const navigate = useNavigate();

  const [index, setIndex] = useState(0);
  const [turn, setTurn] = useState<TurnView | null>(null);
  const [result, setResult] = useState<TurnResult | null>(null);
  /** Ein Zug wird nach einem Fehler genau einmal wiederholt, dann geht es weiter. */
  const [retried, setRetried] = useState(false);
  const [done, setDone] = useState<TurnResult | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    if (!sceneId || !seed) return;
    getTurn(sceneId, seed, index)
      .then(setTurn)
      .catch(() => setError(true));
  }, [sceneId, seed, index]);

  const submit = useCallback(
    (submission: Submission) => {
      if (!sceneId) return;
      answerTurn(sceneId, index, seed, submission)
        .then(setResult)
        .catch(() => setError(true));
    },
    [sceneId, index, seed],
  );

  const retry = () => {
    setResult(null);
    setRetried(true);
  };

  const advance = () => {
    if (result?.scene_completed) {
      setDone(result);
      return;
    }
    setResult(null);
    setRetried(false);
    setIndex((current) => current + 1);
  };

  if (error) return <p>Die Szene konnte nicht geladen werden.</p>;

  if (done) {
    return (
      <section className="mx-auto max-w-3xl space-y-4">
        <h2 className="text-2xl font-semibold">Geschafft!</h2>
        <p>{done.outro_de}</p>
        <button
          type="button"
          onClick={() => navigate(`/dorf/${placeId}`)}
          className="rounded-xl bg-sky-600 px-5 py-2 font-medium text-white"
        >
          Zurück
        </button>
      </section>
    );
  }

  if (!turn) return <p>Szene wird geladen …</p>;

  return (
    <section className="mx-auto max-w-3xl space-y-4">
      <p className="text-sm text-slate-500">
        Zug {turn.index + 1} von {turn.turn_count}
      </p>
      <NpcLine line={turn.npc_line} />

      <BuildSentenceExercise
        key={`${turn.index}-${retried}`}
        exercise={turn.exercise}
        disabled={result !== null}
        onSubmit={submit}
      />

      {result && (
        <div className="space-y-3 rounded-2xl border-2 border-slate-200 p-4">
          {result.npc_reaction && <NpcLine line={result.npc_reaction} />}
          {!result.correct && <p>{result.explanation_de}</p>}
          {!result.correct && !retried ? (
            <button
              type="button"
              onClick={retry}
              className="rounded-xl bg-sky-600 px-5 py-2 font-medium text-white"
            >
              Nochmal
            </button>
          ) : (
            <button
              type="button"
              onClick={advance}
              className="rounded-xl bg-sky-600 px-5 py-2 font-medium text-white"
            >
              Weiter
            </button>
          )}
        </div>
      )}
    </section>
  );
}
```

Hinweis: `BuildSentenceExercise` erwartet einen `onSubmit`-Aufruf über einen eigenen „Prüfen"-Knopf. Sieh in `frontend/src/course/BuildSentenceExercise.tsx` nach, wie der Knopf beschriftet ist, und richte die Tests danach aus, falls er anders heißt als „Prüfen".

- [ ] **Step 5: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/views/SceneView.test.tsx && npx tsc --noEmit -p tsconfig.json`
Expected: PASS (4 Tests)

- [ ] **Step 6: Run the whole frontend suite**

Run: `cd frontend && npx vitest run`
Expected: alle Tests grün

- [ ] **Step 7: Commit**

```bash
git add frontend/src/views/SceneView.tsx frontend/src/views/SceneView.test.tsx frontend/src/game/NpcLine.tsx
git commit -m "feat(game): run a scene turn by turn with one retry per turn"
```

---

### Task 11: Durchgängiger Test

**Files:**
- Create: `frontend/e2e/dorf.spec.ts`

**Interfaces:**
- Consumes: den laufenden Stack, den `playwright.config.ts` selbst startet

- [ ] **Step 1: Write the failing test**

Sieh zuerst in `frontend/e2e/kurs.spec.ts` nach, wie dort navigiert und auf Kacheln geklickt wird, und übernimm dieselben Hilfsmittel und Selektoren.

`frontend/e2e/dorf.spec.ts`:

```ts
import { expect, test } from "@playwright/test";

test.describe("Dorf", () => {
  test("zeigt die Karte mit den Gebäuden", async ({ page }) => {
    await page.goto("/dorf");
    await expect(page.getByAltText("Das Dorf")).toBeVisible();
    await expect(page.getByRole("button", { name: /бар/ })).toBeVisible();
  });

  test("öffnet die Bar und stellt die Leute vor", async ({ page }) => {
    await page.goto("/dorf");
    await page.getByRole("button", { name: /бар/ }).click();
    await expect(page.getByText("Пётр")).toBeVisible();
  });

  test("spricht jemanden an und bringt das Gespräch zu Ende", async ({ page }) => {
    await page.goto("/dorf");
    await page.getByRole("button", { name: /бар/ }).click();
    await page.getByRole("button", { name: /Пётр/ }).click();

    await expect(page.getByText(/Zug 1 von/)).toBeVisible();

    // Beide Züge falsch beantworten: der Weg durch die Szene muss auch dann
    // bis zum Ende fuehren — «Scheitern erlaubt» aus Abschnitt 2 der Spec.
    for (let turn = 0; turn < 2; turn += 1) {
      await page.getByRole("button", { name: "Prüfen" }).click();
      await page.getByRole("button", { name: "Nochmal" }).click();
      await page.getByRole("button", { name: "Prüfen" }).click();
      await page.getByRole("button", { name: "Weiter" }).click();
    }

    await expect(page.getByText("Geschafft!")).toBeVisible();
  });

  test("führt vom Sprachkurs in eine Einheit", async ({ page }) => {
    await page.goto("/dorf");
    await page.getByRole("button", { name: /шко́ла/ }).click();
    await page.getByRole("button", { name: /Einheit \d+ beginnen/ }).click();
    await expect(page).toHaveURL(/\/kurs\/\d+/);
  });
});
```

- [ ] **Step 2: Run the test**

Run: `make test-e2e`
Expected: zunächst rot, falls Beschriftungen abweichen — dann Selektoren an die tatsächliche Oberfläche angleichen, nicht die Oberfläche an den Test.

- [ ] **Step 3: Run everything**

Run: `make validate && make test && make test-e2e`
Expected: alles grün

- [ ] **Step 4: Commit**

```bash
git add frontend/e2e/dorf.spec.ts
git commit -m "test(game): walk through the village end to end"
```

---

### Task 12: Inhalte — Bar, Café und Laden

**Files:**
- Modify: `content/game/npcs.json`
- Create: `content/game/scenes/bar-02.json` … `bar-06.json`
- Create: `content/game/scenes/kafe-01.json`, `kafe-02.json`
- Create: `content/game/scenes/magazin-02.json`
- Create: `content/game/art/npc_*.svg` für die neuen Personen
- Modify: `content/ru/lexicon.json`, falls Wörter fehlen

**Interfaces:**
- Consumes: das Schema aus Task 1, die Regeln aus Task 2

- [ ] **Step 1: Add five people to the bar**

`content/game/npcs.json` um vier weitere Personen an `bar` ergänzen (Pjotr steht schon dort), jeweils mit eigenem `art`-Verweis. Vorschlag: `nadja` (die Wirtin), `sasha` (jung, redet schnell), `oleg` (wortkarg), `vera` (fragt nach der Familie). Für jede eine `npc_*.svg` unter `content/game/art/` zeichnen, `viewBox="0 0 400 400"`.

- [ ] **Step 2: Write five bar scenes**

Je eine Szene pro Person, `bar-02.json` bis `bar-06.json`, drei bis fünf Züge. Themen aus dem vorhandenen Wortschatz:

- Nadja fragt, was du trinkst — Einheiten 25 bis 27
- Sascha fragt, woher du kommst und wo du wohnst — Einheiten 7 und 24
- Oleg fragt, was etwas kostet — Einheit 31
- Vera fragt nach deiner Familie — Einheiten 14 und 23

Regeln beim Schreiben: `hint_unit` auf die Einheit setzen, die den Kern liefert; Ablenker aus Formen desselben Paradigmas oder aus verwandten Wörtern nehmen, nie aus der Lösung; jeder Zug bekommt einen `prompt_de`, der sagt, **was** gesagt werden soll, nicht **wie**.

`content/game/scenes/bar-02.json` als ausgeschriebenes Muster für die übrigen vier — alle Formen darin gibt es bereits im Lexikon:

```json
{
  "id": "bar-02",
  "kind": "dialog",
  "place": "bar",
  "npc": "nadja",
  "title_de": "Nadja hinter der Theke",
  "hint_unit": 31,
  "intro_de": "Die Wirtin wischt die Theke und sieht dich an.",
  "outro_de": "Nadja stellt dir den Tee hin und wendet sich dem nächsten Gast zu.",
  "turns": [
    {
      "npc_line": [["chto", "acc"], ["vy", "nom"], ["pit", "prs.2pl"]],
      "prompt_de": "Sag, dass du einen Tee möchtest.",
      "solution": [["ja", "nom"], ["khotet", "prs.1sg"], ["chaj", "acc.sg"]],
      "distractors": [["khotet", "prs.3sg"], ["kofe", "acc.sg"]]
    },
    {
      "npc_line": [["khorosho", "base"], ["eto", "base"], ["stoit", "prs.3sg"],
                   ["dva", "nom.m"], ["evro", "gen.sg"]],
      "prompt_de": "Sag, dass das nicht teuer ist.",
      "solution": [["eto", "base"], ["ne", "base"], ["dorogo", "base"]],
      "distractors": [["deshjovo", "base"], ["ochen", "base"]]
    },
    {
      "npc_line": [["vy", "nom"], ["zdes", "base"], ["zhit", "prs.2pl"]],
      "prompt_de": "Sag ja und dass du jetzt hier wohnst.",
      "solution": [["da", "base"], ["ja", "nom"], ["zhit", "prs.1sg"], ["zdes", "base"]],
      "distractors": [["zhit", "prs.3sg"], ["tam", "base"]]
    }
  ]
}
```

Gesprochen ergibt das: «Что вы пьёте?» — «Я хочу́ чай.» — «Хорошо́, э́то сто́ит два е́вро.» — «Э́то не до́рого.» — «Вы здесь живёте?» — «Да, я живу́ здесь.»

- [ ] **Step 3: Write two café scenes and a second shopping list**

`kafe-01.json` und `kafe-02.json` als `dialog` — Bestellen und Bezahlen, passend zu den Einheiten 25 bis 32. `magazin-02.json` als zweite `shopping`-Szene mit anderem Pool und `count: 4`.

Dafür braucht `content/game/npcs.json` noch mindestens eine Person am `kafe`.

- [ ] **Step 4: Validate**

Run: `make validate`
Expected: OK mit 4 Orten und 10 Szenen

Meldet der Validator fehlende Lexeme, ergänze sie in `content/ru/lexicon.json` nach den Regeln der Kurs-Spec: vollständiges Formenparadigma, Betonungszeichen, wissenschaftliche Umschrift.

- [ ] **Step 5: Read every Russian sentence back**

Der Validator prüft **keine** Grammatik. Rendere alle Szenen im Klartext und lies sie Form für Form gegen:

```bash
cd backend && .venv/bin/python -c "
from pathlib import Path
from app.content.loader import load_course
from app.game.loader import load_village
from app.game import scenes as s
course = load_course(Path('../content/ru'))
village = load_village(Path('../content/game'))
for scene in sorted(village.scenes.values(), key=lambda x: x.id):
    print('===', scene.id, scene.title_de)
    for turn in s.scene_turns(course, scene, seed='pruefung'):
        npc = ' '.join(course.form(r).text for r in turn.npc_line)
        me  = ' '.join(course.form(r).text for r in turn.solution)
        print(f'  NPC: {npc}')
        print(f'  ICH: {me}   [{turn.prompt_de}]')
"
```

- [ ] **Step 6: Commit**

```bash
git add content/game content/ru/lexicon.json
git commit -m "feat(game): populate the bar, the cafe and the shop"
```

---

### Task 13: Bild-Prompts für eine andere KI

**Files:**
- Create: `content/game/art/PROMPTS.md`

- [ ] **Step 1: Write the prompt collection**

`content/game/art/PROMPTS.md` mit:

1. **Gemeinsame Stilvorgabe** in einem Absatz, den man jedem Einzelprompt voranstellt — damit die Bilder zueinander passen: Jahreszeit, Tageszeit, Farbstimmung, Detailgrad, keine Schrift im Bild (die Beschriftung legt die Oberfläche darüber).
2. **Je ein fertiger Prompt** für `village`, `shkola`, `kafe`, `magazin`, `bar` und jede Person, auf Englisch, damit er bei den gängigen Bildmodellen zuverlässig greift.
3. **Die harten Anforderungen** je Bildart, weil sonst die Klickflächen nicht sitzen: Karte 16:9 mit den vier Gebäuden in dieser Reihenfolge von links nach rechts und an den Anteilen aus `places.json`; Innenansichten 3:2; Personen 1:1.
4. **Was zu tun ist**, wenn die Bilder fertig sind: als `.webp` unter dem Namen des `art`-Verweises in dieses Verzeichnis legen, `make validate` laufen lassen, fertig — die SVG bleiben als Rückfall liegen.

- [ ] **Step 2: Verify the promise holds**

Lege testweise eine beliebige `.webp` als `content/game/art/bar.webp` ab und rufe `/api/game/art/bar` auf. Erwartung: `content-type: image/webp`. Danach die Datei wieder löschen und prüfen, dass wieder das SVG kommt.

- [ ] **Step 3: Commit**

```bash
git add content/game/art/PROMPTS.md
git commit -m "docs(game): add image prompts for generating the village art"
```

---

## Abschluss

Nach Task 13:

```bash
make validate && make test && make test-e2e
```

Alles grün heißt: das Dorf ist begehbar, zehn Szenen liegen bereit, die Bilder lassen sich ohne Codeänderung austauschen.
