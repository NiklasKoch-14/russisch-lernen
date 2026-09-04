# Russisch-Kurs-Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Baut die klick-basierte Übungs-Engine für den Russisch-Anfängerkurs — Content-Format, Validierung, serverseitige Antwortprüfung, Wortform-SRS, Einstufung und die React-Oberfläche — lauffähig mit acht echten Seed-Einheiten.

**Architecture:** Lerninhalte liegen als validiertes JSON unter `content/ru/` und werden beim Start read-only geladen; Sätze referenzieren `(lexeme_id, form_key)`-Paare statt roher Strings. SQLite speichert ausschließlich Fortschritt. Antworten werden serverseitig geprüft: der Client bekommt deterministisch gemischte Kacheln und schickt nur Indizes zurück, sodass die Lösung nie ausgeliefert wird.

**Tech Stack:** Python 3.12 / FastAPI / SQLite / pytest · React 18 / TypeScript / Vite / Tailwind CSS v4 / react-router / Vitest

**Spec:** `docs/superpowers/specs/2026-09-04-speaker-russian-beginner-course-design.md`

## Global Constraints

- Zielsprache ist Russisch; `DEFAULT_LANGUAGE` lautet `russian`.
- UI-Sprache ist durchgehend Deutsch. Alle sichtbaren Texte, Fehlermeldungen und Schaltflächen auf Deutsch.
- Der Lernende tippt nie kyrillisch. Jede Aufgabe ist ausschließlich per Klick lösbar.
- Lerninhalte stammen nie vom LLM. Ollama wird nur für deutsche Erklärungen benutzt und ist immer optional.
- Antwortprüfung findet ausschließlich im Backend statt. Kein Endpunkt liefert die Lösung einer offenen Aufgabe aus.
- Alle kyrillischen Formen mit mehr als einer Silbe tragen ein Betonungszeichen `U+0301`; Ausnahmen sind Einsilber, Formen mit `ё` und Lexeme der Wortart `letter`.
- Keine neue Backend-Abhängigkeit außer den bereits in `backend/requirements.txt` gelisteten.
- Bestehende Endpunkte und Tests bleiben grün; der englische Vokabel-Flow wird nicht entfernt.
- Backend-Tests laufen mit `cd backend && .venv/bin/pytest`, Frontend-Tests mit `cd frontend && npm test`.

## File Structure

**Neu — Content-Daten**
- `content/ru/lexicon.json` — Wortform-Lexikon
- `content/ru/screening.json` — Einstufungssonden
- `content/ru/units/001.json` … `008.json` — Seed-Einheiten

**Neu — Backend**
- `backend/app/content/models.py` — Dataclasses für Lexem, Form, Einheit, Aufgabentypen, Sonde, Kurs
- `backend/app/content/formkeys.py` — erlaubte `form_key`-Werte je Wortart
- `backend/app/content/loader.py` — JSON → Dataclasses
- `backend/app/content/validator.py` — Regeln aus Spec §9
- `backend/app/course/shuffle.py` — deterministisches Mischen
- `backend/app/course/presenter.py` — Aufgabe → Client-Payload ohne Lösung
- `backend/app/course/checker.py` — Antwortprüfung je Aufgabentyp
- `backend/app/course/service.py` — Einheit abschließen, Fortschritt und SRS fortschreiben
- `backend/app/screening/service.py` — adaptive Einstufung
- `backend/app/repositories/progress_repo.py` — `unit_progress`, `exercise_attempts`
- `backend/app/repositories/lexeme_srs_repo.py` — `lexeme_srs`
- `backend/scripts/validate_content.py` — CLI-Validator

**Geändert — Backend**
- `backend/app/config.py` — `default_language`, `content_dir`
- `backend/app/db.py` — neue Tabellen und Spalten-Migration
- `backend/app/dependencies.py` — `get_course()`
- `backend/app/repositories/profile_repo.py` — `show_transliteration`, `placement_unit`
- `backend/app/api/schemas.py`, `backend/app/api/routes.py` — neue Endpunkte

**Neu — Frontend**
- `frontend/src/course/RussianText.tsx`, `Tile.tsx`
- `frontend/src/course/BuildSentenceExercise.tsx`, `ChooseFormExercise.tsx`, `MatchPairsExercise.tsx`, `DialogReplyExercise.tsx`
- `frontend/src/course/ExerciseRunner.tsx` — wählt die Komponente zum Typ
- `frontend/src/views/CourseView.tsx`, `UnitView.tsx`, `ScreeningView.tsx`, `ReviewView.tsx`
- `frontend/src/courseApi.ts`, `frontend/src/courseTypes.ts`
- `frontend/src/index.css` — Tailwind-Einstieg

**Geändert — Frontend**
- `frontend/package.json`, `vite.config.ts`, `src/main.tsx`, `src/App.tsx`

---
## Task 1: Content-Datenmodell und erlaubte Wortformen

**Files:**
- Create: `backend/app/content/__init__.py`
- Create: `backend/app/content/models.py`
- Create: `backend/app/content/formkeys.py`
- Test: `backend/tests/test_content_models.py`

**Interfaces:**
- Consumes: nichts
- Produces: `Form`, `Lexeme`, `GrammarFocus`, `TokenRef`, `BuildSentenceExercise`, `ChooseFormExercise`, `MatchPairsExercise`, `DialogReplyExercise`, `ReplyOption`, `Exercise`, `Unit`, `ScreeningProbe`, `Course` aus `app.content.models`; `allowed_form_keys(pos) -> frozenset[str]` und `POS_VALUES: frozenset[str]` aus `app.content.formkeys`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_content_models.py
import pytest

from app.content.formkeys import POS_VALUES, allowed_form_keys
from app.content.models import Course, Form, Lexeme


def test_verb_form_keys_cover_present_and_past():
    keys = allowed_form_keys("verb")
    assert {"inf", "prs.1sg", "prs.3sg", "pst.f", "imp.sg"} <= keys
    assert "nom.sg" not in keys


def test_noun_form_keys_are_case_number_pairs():
    keys = allowed_form_keys("noun")
    assert {"nom.sg", "acc.sg", "prp.sg", "nom.pl", "ins.pl"} <= keys
    assert len(keys) == 12


def test_invariable_parts_of_speech_only_have_base():
    for pos in ("adv", "prep", "part", "conj", "interj", "letter"):
        assert allowed_form_keys(pos) == frozenset({"base"})


def test_unknown_pos_raises():
    with pytest.raises(KeyError):
        allowed_form_keys("verbb")


def test_pos_values_match_formkey_table():
    assert "verb" in POS_VALUES and "letter" in POS_VALUES


def test_course_lookup_returns_form_text():
    lexeme = Lexeme(
        id="delat",
        lemma="де́лать",
        pos="verb",
        gloss_de="machen, tun",
        forms={"prs.3sg": Form(text="де́лает", translit="délajet")},
    )
    course = Course(language="russian", lexemes={"delat": lexeme}, units={}, screening=[])
    assert course.form(("delat", "prs.3sg")).text == "де́лает"


def test_course_form_raises_for_missing_lexeme():
    course = Course(language="russian", lexemes={}, units={}, screening=[])
    with pytest.raises(KeyError):
        course.form(("nope", "base"))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && .venv/bin/pytest tests/test_content_models.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.content'`

- [ ] **Step 3: Implement the form-key table**

```python
# backend/app/content/formkeys.py
CASES = ("nom", "gen", "dat", "acc", "ins", "prp")
NUMBERS = ("sg", "pl")
GENDERS = ("m", "f", "n", "pl")
PERSONS = ("1sg", "2sg", "3sg", "1pl", "2pl", "3pl")

_VERB = frozenset(
    ["inf"]
    + [f"prs.{p}" for p in PERSONS]
    + [f"fut.{p}" for p in PERSONS]
    + [f"pst.{g}" for g in ("m", "f", "n", "pl")]
    + ["imp.sg", "imp.pl"]
)
_NOUN = frozenset(f"{c}.{n}" for c in CASES for n in NUMBERS)
_ADJ = frozenset(f"{c}.{g}" for c in CASES for g in GENDERS)
_CASE_ONLY = frozenset(CASES)
_BASE = frozenset({"base"})

FORM_KEYS: dict[str, frozenset[str]] = {
    "verb": _VERB,
    "noun": _NOUN,
    "adj": _ADJ,
    "pron": _CASE_ONLY,
    "num": _CASE_ONLY,
    "adv": _BASE,
    "prep": _BASE,
    "part": _BASE,
    "conj": _BASE,
    "interj": _BASE,
    "letter": _BASE,
}

POS_VALUES = frozenset(FORM_KEYS)


def allowed_form_keys(pos: str) -> frozenset[str]:
    """Return the form keys a lexeme of this part of speech may declare."""
    return FORM_KEYS[pos]
```

- [ ] **Step 4: Implement the dataclasses**

```python
# backend/app/content/models.py
from dataclasses import dataclass, field

TokenRef = tuple[str, str]
"""A (lexeme_id, form_key) pair — how every sentence token is written in content."""


@dataclass(frozen=True)
class Form:
    text: str
    translit: str


@dataclass(frozen=True)
class Lexeme:
    id: str
    lemma: str
    pos: str
    gloss_de: str
    forms: dict[str, Form]
    aspect: str | None = None
    aspect_pair: str | None = None


@dataclass(frozen=True)
class GrammarFocus:
    id: str
    title_de: str
    explanation_de: str


@dataclass(frozen=True)
class BuildSentenceExercise:
    id: str
    prompt_de: str
    solution: list[TokenRef]
    distractors: list[TokenRef]
    type: str = "build_sentence"


@dataclass(frozen=True)
class ChooseFormExercise:
    id: str
    prompt_de: str
    sentence: list[TokenRef | None]
    answer: TokenRef
    distractor_forms: list[str]
    type: str = "choose_form"


@dataclass(frozen=True)
class MatchPairsExercise:
    id: str
    prompt_de: str
    pairs: list[TokenRef]
    type: str = "match_pairs"


@dataclass(frozen=True)
class ReplyOption:
    tokens: list[TokenRef]
    why_de: str


@dataclass(frozen=True)
class DialogReplyExercise:
    id: str
    prompt_de: str
    tutor_line: list[TokenRef]
    options: list[ReplyOption]
    correct_index: int
    type: str = "dialog_reply"


Exercise = (
    BuildSentenceExercise | ChooseFormExercise | MatchPairsExercise | DialogReplyExercise
)


@dataclass(frozen=True)
class Unit:
    id: int
    stage: int
    title_de: str
    scenario_de: str
    grammar_focus: GrammarFocus
    new_lexemes: list[str]
    exercises: list[Exercise]


@dataclass(frozen=True)
class ScreeningProbe:
    id: str
    prompt_de: str
    options: list[str]
    correct_index: int
    maps_to_unit: int


@dataclass(frozen=True)
class Course:
    language: str
    lexemes: dict[str, Lexeme]
    units: dict[int, Unit]
    screening: list[ScreeningProbe] = field(default_factory=list)

    def form(self, ref: TokenRef) -> Form:
        """Resolve a token reference to its concrete word form."""
        lexeme_id, form_key = ref
        lexeme = self.lexemes[lexeme_id]
        return lexeme.forms[form_key]

    def gloss(self, ref: TokenRef) -> str:
        return self.lexemes[ref[0]].gloss_de

    def ordered_units(self) -> list[Unit]:
        return [self.units[key] for key in sorted(self.units)]
```

Create `backend/app/content/__init__.py` as an empty file.

- [ ] **Step 5: Run test to verify it passes**

Run: `cd backend && .venv/bin/pytest tests/test_content_models.py -v`
Expected: PASS (7 tests)

- [ ] **Step 6: Commit**

```bash
git add backend/app/content backend/tests/test_content_models.py
git commit -m "feat: add russian course content data model"
```

---
## Task 2: Content-Loader

**Files:**
- Create: `backend/app/content/loader.py`
- Test: `backend/tests/test_content_loader.py`
- Test: `backend/tests/content_factory.py`

**Interfaces:**
- Consumes: alle Dataclasses aus `app.content.models`
- Produces: `load_course(content_dir: str | Path, language: str = "russian") -> Course` und `ContentError(Exception)` aus `app.content.loader`; Testhelfer `write_course(root, lexemes=..., units=..., screening=...)` aus `tests.content_factory`

Der Loader liest `lexicon.json`, alle `units/*.json` und `screening.json`. In JSON werden Token als zweielementige Listen `["delat", "prs.3sg"]` geschrieben; die Lücke in `choose_form.sentence` als Zeichenkette `"___"`. Der Loader wandelt beides in `TokenRef` bzw. `None` um. Er prüft **Struktur**, nicht Inhalt — inhaltliche Regeln gehören in Task 3.

- [ ] **Step 1: Write the test factory**

```python
# backend/tests/content_factory.py
import json
from pathlib import Path

MINIMAL_LEXICON = {
    "version": 1,
    "lexemes": [
        {
            "id": "ja",
            "lemma": "я",
            "pos": "pron",
            "gloss_de": "ich",
            "forms": {"nom": {"text": "я", "translit": "ja"}},
        },
        {
            "id": "delat",
            "lemma": "де́лать",
            "pos": "verb",
            "gloss_de": "machen, tun",
            "aspect": "impf",
            "forms": {
                "prs.1sg": {"text": "де́лаю", "translit": "délaju"},
                "prs.2sg": {"text": "де́лаешь", "translit": "délaješ'"},
                "prs.3sg": {"text": "де́лает", "translit": "délajet"},
            },
        },
    ],
}

MINIMAL_UNIT = {
    "id": 1,
    "stage": 0,
    "title_de": "Was machst du?",
    "scenario_de": "Du fragst jemanden nach seiner Tätigkeit.",
    "grammar_focus": {
        "id": "prs-conj",
        "title_de": "Verbendungen im Präsens",
        "explanation_de": "Die Endung zeigt, wer handelt.",
    },
    "new_lexemes": ["ja", "delat"],
    "exercises": [
        {
            "id": "1-1",
            "type": "build_sentence",
            "prompt_de": "Ich mache das.",
            "solution": [["ja", "nom"], ["delat", "prs.1sg"]],
            "distractors": [["delat", "prs.3sg"]],
        },
        {
            "id": "1-2",
            "type": "choose_form",
            "prompt_de": "Was macht er?",
            "sentence": [["ja", "nom"], "___"],
            "answer": ["delat", "prs.1sg"],
            "distractor_forms": ["prs.2sg", "prs.3sg"],
        },
        {
            "id": "1-3",
            "type": "match_pairs",
            "prompt_de": "Ordne zu.",
            "pairs": [["ja", "nom"], ["delat", "prs.1sg"]],
        },
        {
            "id": "1-4",
            "type": "dialog_reply",
            "prompt_de": "Wie antwortest du?",
            "tutor_line": [["delat", "prs.2sg"]],
            "correct_index": 0,
            "options": [
                {"tokens": [["ja", "nom"], ["delat", "prs.1sg"]], "why_de": ""},
                {"tokens": [["delat", "prs.3sg"]], "why_de": "Das ist die Form für er/sie."},
            ],
        },
    ],
}

MINIMAL_SCREENING = [
    {
        "id": "s1",
        "prompt_de": "Welcher Buchstabe klingt wie ein r?",
        "options": ["Р", "П", "Н"],
        "correct_index": 0,
        "maps_to_unit": 1,
    }
]


def write_course(root, *, lexicon=None, units=None, screening=None) -> Path:
    """Write a course tree under root and return the content directory."""
    content = Path(root) / "ru"
    (content / "units").mkdir(parents=True, exist_ok=True)
    (content / "lexicon.json").write_text(
        json.dumps(lexicon if lexicon is not None else MINIMAL_LEXICON), encoding="utf-8"
    )
    (content / "screening.json").write_text(
        json.dumps(
            {"probes": screening if screening is not None else MINIMAL_SCREENING}
        ),
        encoding="utf-8",
    )
    for unit in units if units is not None else [MINIMAL_UNIT]:
        (content / "units" / f"{unit['id']:03d}.json").write_text(
            json.dumps(unit), encoding="utf-8"
        )
    return content
```

- [ ] **Step 2: Write the failing loader test**

```python
# backend/tests/test_content_loader.py
import json

import pytest

from app.content.loader import ContentError, load_course
from app.content.models import (
    BuildSentenceExercise,
    ChooseFormExercise,
    DialogReplyExercise,
    MatchPairsExercise,
)
from tests.content_factory import MINIMAL_UNIT, write_course


def test_loads_lexemes_with_forms(tmp_path):
    course = load_course(write_course(tmp_path))
    assert course.lexemes["delat"].pos == "verb"
    assert course.lexemes["delat"].forms["prs.3sg"].text == "де́лает"
    assert course.lexemes["delat"].aspect == "impf"


def test_loads_units_keyed_by_id(tmp_path):
    course = load_course(write_course(tmp_path))
    assert set(course.units) == {1}
    assert course.units[1].grammar_focus.title_de == "Verbendungen im Präsens"


def test_token_lists_become_tuples(tmp_path):
    exercise = load_course(write_course(tmp_path)).units[1].exercises[0]
    assert isinstance(exercise, BuildSentenceExercise)
    assert exercise.solution == [("ja", "nom"), ("delat", "prs.1sg")]
    assert exercise.distractors == [("delat", "prs.3sg")]


def test_blank_marker_becomes_none(tmp_path):
    exercise = load_course(write_course(tmp_path)).units[1].exercises[1]
    assert isinstance(exercise, ChooseFormExercise)
    assert exercise.sentence == [("ja", "nom"), None]
    assert exercise.answer == ("delat", "prs.1sg")


def test_loads_match_pairs_and_dialog_reply(tmp_path):
    exercises = load_course(write_course(tmp_path)).units[1].exercises
    assert isinstance(exercises[2], MatchPairsExercise)
    assert exercises[2].pairs == [("ja", "nom"), ("delat", "prs.1sg")]
    assert isinstance(exercises[3], DialogReplyExercise)
    assert exercises[3].options[1].why_de.startswith("Das ist die Form")


def test_loads_screening_probes(tmp_path):
    course = load_course(write_course(tmp_path))
    assert course.screening[0].maps_to_unit == 1


def test_units_are_sorted_by_id(tmp_path):
    second = dict(MINIMAL_UNIT, id=2)
    course = load_course(write_course(tmp_path, units=[second, MINIMAL_UNIT]))
    assert [unit.id for unit in course.ordered_units()] == [1, 2]


def test_unknown_exercise_type_raises_content_error(tmp_path):
    broken = dict(MINIMAL_UNIT, exercises=[{"id": "1-1", "type": "sing_a_song"}])
    with pytest.raises(ContentError, match="sing_a_song"):
        load_course(write_course(tmp_path, units=[broken]))


def test_missing_lexicon_raises_content_error(tmp_path):
    content = write_course(tmp_path)
    (content / "lexicon.json").unlink()
    with pytest.raises(ContentError, match="lexicon.json"):
        load_course(content)


def test_malformed_json_raises_content_error(tmp_path):
    content = write_course(tmp_path)
    (content / "units" / "001.json").write_text("{not json", encoding="utf-8")
    with pytest.raises(ContentError, match="001.json"):
        load_course(content)


def test_duplicate_unit_id_raises_content_error(tmp_path):
    content = write_course(tmp_path)
    (content / "units" / "009.json").write_text(
        json.dumps(MINIMAL_UNIT), encoding="utf-8"
    )
    with pytest.raises(ContentError, match="doppelt"):
        load_course(content)
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd backend && .venv/bin/pytest tests/test_content_loader.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.content.loader'`

- [ ] **Step 4: Implement the loader**

```python
# backend/app/content/loader.py
import json
from pathlib import Path

from app.content.models import (
    BuildSentenceExercise,
    ChooseFormExercise,
    Course,
    DialogReplyExercise,
    Exercise,
    Form,
    GrammarFocus,
    Lexeme,
    MatchPairsExercise,
    ReplyOption,
    ScreeningProbe,
    TokenRef,
    Unit,
)

BLANK = "___"


class ContentError(Exception):
    """Raised when the content package cannot be read or is structurally invalid."""


def _read_json(path: Path) -> dict | list:
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


def _lexeme(raw: dict) -> Lexeme:
    try:
        forms = {
            key: Form(text=value["text"], translit=value["translit"])
            for key, value in raw["forms"].items()
        }
        return Lexeme(
            id=raw["id"],
            lemma=raw["lemma"],
            pos=raw["pos"],
            gloss_de=raw["gloss_de"],
            forms=forms,
            aspect=raw.get("aspect"),
            aspect_pair=raw.get("aspect_pair"),
        )
    except (KeyError, TypeError) as exc:
        raise ContentError(f"Lexem unvollständig: {raw.get('id', raw)!r} ({exc})") from exc


def _exercise(raw: dict, unit_id: int) -> Exercise:
    kind = raw.get("type")
    where = f"Einheit {unit_id}, Aufgabe {raw.get('id')}"
    try:
        if kind == "build_sentence":
            return BuildSentenceExercise(
                id=raw["id"],
                prompt_de=raw["prompt_de"],
                solution=_tokens(raw["solution"], where),
                distractors=_tokens(raw.get("distractors", []), where),
            )
        if kind == "choose_form":
            sentence: list[TokenRef | None] = [
                None if item == BLANK else _token(item, where) for item in raw["sentence"]
            ]
            return ChooseFormExercise(
                id=raw["id"],
                prompt_de=raw["prompt_de"],
                sentence=sentence,
                answer=_token(raw["answer"], where),
                distractor_forms=list(raw["distractor_forms"]),
            )
        if kind == "match_pairs":
            return MatchPairsExercise(
                id=raw["id"],
                prompt_de=raw["prompt_de"],
                pairs=_tokens(raw["pairs"], where),
            )
        if kind == "dialog_reply":
            options = [
                ReplyOption(tokens=_tokens(option["tokens"], where), why_de=option.get("why_de", ""))
                for option in raw["options"]
            ]
            return DialogReplyExercise(
                id=raw["id"],
                prompt_de=raw["prompt_de"],
                tutor_line=_tokens(raw["tutor_line"], where),
                options=options,
                correct_index=int(raw["correct_index"]),
            )
    except KeyError as exc:
        raise ContentError(f"{where}: Feld fehlt {exc}") from exc
    raise ContentError(f"{where}: unbekannter Aufgabentyp {kind!r}")


def _unit(raw: dict, source: Path) -> Unit:
    try:
        focus = raw["grammar_focus"]
        return Unit(
            id=int(raw["id"]),
            stage=int(raw["stage"]),
            title_de=raw["title_de"],
            scenario_de=raw["scenario_de"],
            grammar_focus=GrammarFocus(
                id=focus["id"],
                title_de=focus["title_de"],
                explanation_de=focus["explanation_de"],
            ),
            new_lexemes=list(raw["new_lexemes"]),
            exercises=[_exercise(item, int(raw["id"])) for item in raw["exercises"]],
        )
    except KeyError as exc:
        raise ContentError(f"{source.name}: Feld fehlt {exc}") from exc


def load_course(content_dir: str | Path, language: str = "russian") -> Course:
    """Load the whole content package from disk into an immutable Course."""
    root = Path(content_dir)
    raw_lexicon = _read_json(root / "lexicon.json")
    lexemes = {item["id"]: _lexeme(item) for item in raw_lexicon["lexemes"]}

    units: dict[int, Unit] = {}
    for path in sorted((root / "units").glob("*.json")):
        unit = _unit(_read_json(path), path)
        if unit.id in units:
            raise ContentError(f"Einheiten-ID {unit.id} kommt doppelt vor ({path.name})")
        units[unit.id] = unit

    raw_screening = _read_json(root / "screening.json")
    screening = [
        ScreeningProbe(
            id=probe["id"],
            prompt_de=probe["prompt_de"],
            options=list(probe["options"]),
            correct_index=int(probe["correct_index"]),
            maps_to_unit=int(probe["maps_to_unit"]),
        )
        for probe in raw_screening["probes"]
    ]

    return Course(language=language, lexemes=lexemes, units=units, screening=screening)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd backend && .venv/bin/pytest tests/test_content_loader.py -v`
Expected: PASS (11 tests)

- [ ] **Step 6: Commit**

```bash
git add backend/app/content/loader.py backend/tests/test_content_loader.py backend/tests/content_factory.py
git commit -m "feat: add content loader for russian course package"
```

---
## Task 3: Content-Validator und CLI

**Files:**
- Create: `backend/app/content/validator.py`
- Create: `backend/scripts/validate_content.py`
- Test: `backend/tests/test_content_validator.py`

**Interfaces:**
- Consumes: `Course` und die Aufgaben-Dataclasses aus `app.content.models`, `allowed_form_keys` aus `app.content.formkeys`
- Produces: `validate_course(course: Course) -> list[str]` (leere Liste = fehlerfrei) und `STAGE_RANGES: dict[int, tuple[int, int]]` aus `app.content.validator`

Implementiert die zehn Regeln aus Spec §9. Der Validator gibt **alle** Verstöße als deutschsprachige Meldungen zurück, statt beim ersten abzubrechen — beim Autorieren von 100 Einheiten ist eine vollständige Liste pro Lauf viel wert.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_content_validator.py
import copy

from app.content.loader import load_course
from app.content.validator import STAGE_RANGES, validate_course
from tests.content_factory import MINIMAL_LEXICON, MINIMAL_UNIT, write_course

EXTRA_EXERCISES = [
    dict(MINIMAL_UNIT["exercises"][0], id=f"1-{index}") for index in range(5, 8)
]
GOOD_UNIT = dict(MINIMAL_UNIT, exercises=MINIMAL_UNIT["exercises"] + EXTRA_EXERCISES)


def _course(tmp_path, *, lexicon=None, units=None, screening=None):
    return load_course(
        write_course(tmp_path, lexicon=lexicon, units=units or [GOOD_UNIT], screening=screening)
    )


def test_valid_course_has_no_errors(tmp_path):
    assert validate_course(_course(tmp_path)) == []


def test_reports_unknown_lexeme_reference(tmp_path):
    unit = copy.deepcopy(GOOD_UNIT)
    unit["exercises"][0]["solution"] = [["nope", "nom"]]
    errors = validate_course(_course(tmp_path, units=[unit]))
    assert any("nope" in error for error in errors)


def test_reports_form_key_missing_from_lexeme(tmp_path):
    unit = copy.deepcopy(GOOD_UNIT)
    unit["exercises"][0]["solution"] = [["delat", "pst.f"]]
    errors = validate_course(_course(tmp_path, units=[unit]))
    assert any("pst.f" in error for error in errors)


def test_reports_form_key_not_allowed_for_pos(tmp_path):
    lexicon = copy.deepcopy(MINIMAL_LEXICON)
    lexicon["lexemes"][1]["forms"]["nom.sg"] = {"text": "де́ло", "translit": "délo"}
    errors = validate_course(_course(tmp_path, lexicon=lexicon))
    assert any("nom.sg" in error and "verb" in error for error in errors)


def test_reports_missing_stress_mark(tmp_path):
    lexicon = copy.deepcopy(MINIMAL_LEXICON)
    lexicon["lexemes"][1]["forms"]["prs.1sg"]["text"] = "делаю"
    errors = validate_course(_course(tmp_path, lexicon=lexicon))
    assert any("Betonung" in error for error in errors)


def test_monosyllabic_form_needs_no_stress_mark(tmp_path):
    assert validate_course(_course(tmp_path)) == []


def test_yo_counts_as_stressed(tmp_path):
    lexicon = copy.deepcopy(MINIMAL_LEXICON)
    lexicon["lexemes"].append(
        {
            "id": "ejo",
            "lemma": "её",
            "pos": "pron",
            "gloss_de": "ihr, sie",
            "forms": {"acc": {"text": "её", "translit": "jejó"}},
        }
    )
    assert validate_course(_course(tmp_path, lexicon=lexicon)) == []


def test_reports_empty_translit_or_gloss(tmp_path):
    lexicon = copy.deepcopy(MINIMAL_LEXICON)
    lexicon["lexemes"][0]["gloss_de"] = ""
    lexicon["lexemes"][1]["forms"]["prs.1sg"]["translit"] = ""
    errors = validate_course(_course(tmp_path, lexicon=lexicon))
    assert len(errors) == 2


def test_reports_lexeme_used_before_it_is_introduced(tmp_path):
    first = copy.deepcopy(GOOD_UNIT)
    first["new_lexemes"] = ["ja"]
    errors = validate_course(_course(tmp_path, units=[first]))
    assert any("delat" in error and "eingeführt" in error for error in errors)


def test_lexeme_introduced_earlier_may_be_reused(tmp_path):
    first = copy.deepcopy(GOOD_UNIT)
    second = copy.deepcopy(GOOD_UNIT)
    second["id"] = 2
    second["new_lexemes"] = []
    second["exercises"] = [dict(ex, id=f"2-{i}") for i, ex in enumerate(second["exercises"])]
    assert validate_course(_course(tmp_path, units=[first, second])) == []


def test_reports_distractor_equal_to_solution(tmp_path):
    unit = copy.deepcopy(GOOD_UNIT)
    unit["exercises"][0]["distractors"] = [["delat", "prs.1sg"]]
    errors = validate_course(_course(tmp_path, units=[unit]))
    assert any("Ablenker" in error for error in errors)


def test_reports_distractor_form_from_other_lexeme_paradigm(tmp_path):
    unit = copy.deepcopy(GOOD_UNIT)
    unit["exercises"][1]["distractor_forms"] = ["nom"]
    errors = validate_course(_course(tmp_path, units=[unit]))
    assert any("nom" in error and "Paradigma" in error for error in errors)


def test_reports_too_few_exercises(tmp_path):
    unit = copy.deepcopy(MINIMAL_UNIT)
    errors = validate_course(_course(tmp_path, units=[unit]))
    assert any("mindestens 6" in error for error in errors)


def test_reports_empty_explanation(tmp_path):
    unit = copy.deepcopy(GOOD_UNIT)
    unit["grammar_focus"]["explanation_de"] = "   "
    errors = validate_course(_course(tmp_path, units=[unit]))
    assert any("Erklärung" in error for error in errors)


def test_reports_gap_in_unit_ids(tmp_path):
    third = copy.deepcopy(GOOD_UNIT)
    third["id"] = 3
    third["exercises"] = [dict(ex, id=f"3-{i}") for i, ex in enumerate(third["exercises"])]
    errors = validate_course(_course(tmp_path, units=[GOOD_UNIT, third]))
    assert any("Lücke" in error for error in errors)


def test_reports_stage_mismatch(tmp_path):
    unit = copy.deepcopy(GOOD_UNIT)
    unit["stage"] = 4
    errors = validate_course(_course(tmp_path, units=[unit]))
    assert any("Stufe" in error for error in errors)


def test_reports_screening_probe_pointing_at_missing_unit(tmp_path):
    probes = [
        {
            "id": "s1",
            "prompt_de": "?",
            "options": ["А", "Б"],
            "correct_index": 0,
            "maps_to_unit": 99,
        }
    ]
    errors = validate_course(_course(tmp_path, screening=probes))
    assert any("99" in error for error in errors)


def test_stage_ranges_cover_one_to_hundred(tmp_path):
    assert STAGE_RANGES[0] == (1, 4)
    assert STAGE_RANGES[4][1] == 100
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && .venv/bin/pytest tests/test_content_validator.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.content.validator'`

- [ ] **Step 3: Implement the validator**

```python
# backend/app/content/validator.py
from app.content.formkeys import allowed_form_keys
from app.content.models import (
    BuildSentenceExercise,
    ChooseFormExercise,
    Course,
    DialogReplyExercise,
    Exercise,
    MatchPairsExercise,
    TokenRef,
    Unit,
)

STRESS = "́"
VOWELS = set("аеёиоуыэюяАЕЁИОУЫЭЮЯ")
MIN_EXERCISES = 6

STAGE_RANGES: dict[int, tuple[int, int]] = {
    0: (1, 4),
    1: (5, 24),
    2: (25, 52),
    3: (53, 78),
    4: (79, 100),
}


def _syllables(text: str) -> int:
    return sum(1 for char in text if char in VOWELS)


def _check_lexicon(course: Course) -> list[str]:
    errors: list[str] = []
    for lexeme in course.lexemes.values():
        if lexeme.pos not in ("verb", "noun", "adj", "pron", "num", "adv", "prep", "part", "conj", "interj", "letter"):
            errors.append(f"Lexem {lexeme.id}: unbekannte Wortart {lexeme.pos!r}")
            continue
        if not lexeme.gloss_de.strip():
            errors.append(f"Lexem {lexeme.id}: gloss_de ist leer")
        allowed = allowed_form_keys(lexeme.pos)
        for key, form in lexeme.forms.items():
            if key not in allowed:
                errors.append(
                    f"Lexem {lexeme.id}: Formschlüssel {key!r} ist für Wortart {lexeme.pos!r} nicht erlaubt"
                )
            if not form.translit.strip():
                errors.append(f"Lexem {lexeme.id}, Form {key}: translit ist leer")
            if lexeme.pos == "letter":
                continue
            if _syllables(form.text) > 1 and STRESS not in form.text and "ё" not in form.text:
                errors.append(f"Lexem {lexeme.id}, Form {key}: Betonung fehlt in {form.text!r}")
            if form.text.count(STRESS) > 1:
                errors.append(f"Lexem {lexeme.id}, Form {key}: mehr als eine Betonung in {form.text!r}")
    return errors


def _exercise_tokens(exercise: Exercise) -> list[TokenRef]:
    if isinstance(exercise, BuildSentenceExercise):
        return exercise.solution + exercise.distractors
    if isinstance(exercise, ChooseFormExercise):
        return [token for token in exercise.sentence if token is not None] + [exercise.answer]
    if isinstance(exercise, MatchPairsExercise):
        return list(exercise.pairs)
    if isinstance(exercise, DialogReplyExercise):
        tokens = list(exercise.tutor_line)
        for option in exercise.options:
            tokens.extend(option.tokens)
        return tokens
    return []


def _check_token(course: Course, token: TokenRef, where: str) -> list[str]:
    lexeme_id, form_key = token
    lexeme = course.lexemes.get(lexeme_id)
    if lexeme is None:
        return [f"{where}: Lexem {lexeme_id!r} existiert nicht im Lexikon"]
    if form_key not in lexeme.forms:
        return [f"{where}: Lexem {lexeme_id!r} hat keine Form {form_key!r}"]
    return []


def _check_exercise(course: Course, unit: Unit, exercise: Exercise) -> list[str]:
    where = f"Einheit {unit.id}, Aufgabe {exercise.id}"
    errors: list[str] = []
    for token in _exercise_tokens(exercise):
        errors.extend(_check_token(course, token, where))

    if isinstance(exercise, BuildSentenceExercise):
        overlap = set(exercise.distractors) & set(exercise.solution)
        if overlap:
            errors.append(f"{where}: Ablenker {sorted(overlap)} sind Teil der Lösung")
    if isinstance(exercise, ChooseFormExercise):
        lexeme_id, answer_key = exercise.answer
        lexeme = course.lexemes.get(lexeme_id)
        if answer_key in exercise.distractor_forms:
            errors.append(f"{where}: Ablenker enthält die richtige Form {answer_key!r}")
        if lexeme is not None:
            for key in exercise.distractor_forms:
                if key not in lexeme.forms:
                    errors.append(
                        f"{where}: Ablenkerform {key!r} fehlt im Paradigma von {lexeme_id!r}"
                    )
        if None not in exercise.sentence:
            errors.append(f"{where}: sentence enthält keine Lücke")
    if isinstance(exercise, DialogReplyExercise):
        if not 0 <= exercise.correct_index < len(exercise.options):
            errors.append(f"{where}: correct_index {exercise.correct_index} liegt außerhalb der Optionen")
        for index, option in enumerate(exercise.options):
            if index != exercise.correct_index and not option.why_de.strip():
                errors.append(f"{where}: falsche Option {index} hat keine Begründung (why_de)")
    if isinstance(exercise, MatchPairsExercise) and len(exercise.pairs) < 2:
        errors.append(f"{where}: braucht mindestens 2 Paare")
    return errors


def _check_units(course: Course) -> list[str]:
    errors: list[str] = []
    introduced: set[str] = set()
    ordered = course.ordered_units()

    for position, unit in enumerate(ordered, start=1):
        if unit.id != position:
            errors.append(f"Einheiten-IDs haben eine Lücke: erwartet {position}, gefunden {unit.id}")
        low, high = STAGE_RANGES.get(unit.stage, (0, 0))
        if not low <= unit.id <= high:
            errors.append(f"Einheit {unit.id}: Stufe {unit.stage} passt nicht zum ID-Bereich {low}-{high}")
        if not unit.grammar_focus.explanation_de.strip():
            errors.append(f"Einheit {unit.id}: Erklärung des Grammatik-Fokus ist leer")
        if len(unit.exercises) < MIN_EXERCISES:
            errors.append(f"Einheit {unit.id}: braucht mindestens 6 Aufgaben, hat {len(unit.exercises)}")

        for lexeme_id in unit.new_lexemes:
            if lexeme_id not in course.lexemes:
                errors.append(f"Einheit {unit.id}: neues Lexem {lexeme_id!r} fehlt im Lexikon")
        introduced.update(unit.new_lexemes)

        seen_ids: set[str] = set()
        for exercise in unit.exercises:
            if exercise.id in seen_ids:
                errors.append(f"Einheit {unit.id}: Aufgaben-ID {exercise.id!r} kommt doppelt vor")
            seen_ids.add(exercise.id)
            errors.extend(_check_exercise(course, unit, exercise))
            for lexeme_id, _ in _exercise_tokens(exercise):
                if lexeme_id in course.lexemes and lexeme_id not in introduced:
                    errors.append(
                        f"Einheit {unit.id}, Aufgabe {exercise.id}: "
                        f"Lexem {lexeme_id!r} wird benutzt, bevor es eingeführt wurde"
                    )
    return errors


def _check_screening(course: Course) -> list[str]:
    errors: list[str] = []
    for probe in course.screening:
        if probe.maps_to_unit not in course.units:
            errors.append(f"Screening-Sonde {probe.id}: verweist auf Einheit {probe.maps_to_unit}, die es nicht gibt")
        if not 0 <= probe.correct_index < len(probe.options):
            errors.append(f"Screening-Sonde {probe.id}: correct_index liegt außerhalb der Optionen")
        if len(probe.options) < 2:
            errors.append(f"Screening-Sonde {probe.id}: braucht mindestens 2 Optionen")
    return errors


def validate_course(course: Course) -> list[str]:
    """Return every content rule violation as a German message; empty means valid."""
    return _check_lexicon(course) + _check_units(course) + _check_screening(course)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && .venv/bin/pytest tests/test_content_validator.py -v`
Expected: PASS (18 tests)

- [ ] **Step 5: Add the CLI wrapper**

```python
# backend/scripts/validate_content.py
"""Validate the course content package. Usage: python -m scripts.validate_content [dir]"""
import sys
from pathlib import Path

from app.content.loader import ContentError, load_course
from app.content.validator import validate_course

DEFAULT_DIR = Path(__file__).resolve().parents[2] / "content" / "ru"


def main(argv: list[str]) -> int:
    content_dir = Path(argv[1]) if len(argv) > 1 else DEFAULT_DIR
    try:
        course = load_course(content_dir)
    except ContentError as exc:
        print(f"FEHLER beim Laden: {exc}")
        return 2

    errors = validate_course(course)
    if errors:
        print(f"{len(errors)} Problem(e) in {content_dir}:")
        for error in errors:
            print(f"  - {error}")
        return 1

    print(f"OK — {len(course.units)} Einheiten, {len(course.lexemes)} Lexeme, {len(course.screening)} Sonden")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
```

- [ ] **Step 6: Commit**

```bash
git add backend/app/content/validator.py backend/scripts/validate_content.py backend/tests/test_content_validator.py
git commit -m "feat: add content validator with German rule messages"
```

---
## Task 4: Aufgaben-Darstellung und serverseitige Antwortprüfung

**Files:**
- Create: `backend/app/course/__init__.py`
- Create: `backend/app/course/shuffle.py`
- Create: `backend/app/course/presenter.py`
- Create: `backend/app/course/checker.py`
- Test: `backend/tests/test_course_presenter.py`
- Test: `backend/tests/test_course_checker.py`

**Interfaces:**
- Consumes: `Course`, Aufgaben-Dataclasses aus `app.content.models`
- Produces:
  - `shuffled_order(seed: str, count: int) -> list[int]` aus `app.course.shuffle`
  - `present_exercise(course: Course, exercise: Exercise) -> dict` aus `app.course.presenter`
  - `check_answer(course: Course, exercise: Exercise, submission: dict) -> CheckResult` und die Dataclass `CheckResult(correct: bool, solution_text: str, solution_translit: str, explanation_de: str, trained_forms: list[TokenRef])` aus `app.course.checker`

**Warum deterministisches Mischen:** Der Client bekommt Kacheln in zufälliger, aber aus der Aufgaben-ID reproduzierbarer Reihenfolge und schickt nur Indizes zurück. Der Server mischt beim Prüfen erneut und weiß dadurch, welche Kachel welcher Index war — ohne Serverstate und ohne die Lösung je auszuliefern.

- [ ] **Step 1: Write the failing presenter test**

```python
# backend/tests/test_course_presenter.py
from app.content.loader import load_course
from app.course.presenter import present_exercise
from app.course.shuffle import shuffled_order
from tests.content_factory import write_course


def _course(tmp_path):
    return load_course(write_course(tmp_path))


def test_shuffled_order_is_a_permutation():
    order = shuffled_order("1-1", 5)
    assert sorted(order) == [0, 1, 2, 3, 4]


def test_shuffled_order_is_stable_for_same_seed():
    assert shuffled_order("1-1", 6) == shuffled_order("1-1", 6)


def test_shuffled_order_differs_between_seeds():
    assert shuffled_order("1-1", 8) != shuffled_order("1-2", 8)


def test_build_sentence_payload_has_tiles_without_solution(tmp_path):
    course = _course(tmp_path)
    payload = present_exercise(course, course.units[1].exercises[0])
    assert payload["type"] == "build_sentence"
    assert len(payload["tiles"]) == 3
    assert {tile["text"] for tile in payload["tiles"]} == {"я", "де́лаю", "де́лает"}
    assert [tile["index"] for tile in payload["tiles"]] == [0, 1, 2]
    assert "solution" not in payload and "distractors" not in payload


def test_choose_form_payload_marks_the_blank(tmp_path):
    course = _course(tmp_path)
    payload = present_exercise(course, course.units[1].exercises[1])
    assert payload["sentence"][0]["text"] == "я"
    assert payload["sentence"][1] is None
    assert len(payload["options"]) == 3
    assert "answer" not in payload


def test_match_pairs_payload_shuffles_sides_independently(tmp_path):
    course = _course(tmp_path)
    payload = present_exercise(course, course.units[1].exercises[2])
    assert {item["text"] for item in payload["left"]} == {"я", "де́лаю"}
    assert {item["gloss_de"] for item in payload["right"]} == {"ich", "machen, tun"}


def test_dialog_reply_payload_hides_correct_index(tmp_path):
    course = _course(tmp_path)
    payload = present_exercise(course, course.units[1].exercises[3])
    assert payload["tutor_line"][0]["text"] == "де́лаешь"
    assert len(payload["options"]) == 2
    assert "correct_index" not in payload
    assert all("why_de" not in option for option in payload["options"])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && .venv/bin/pytest tests/test_course_presenter.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.course'`

- [ ] **Step 3: Implement shuffle and presenter**

```python
# backend/app/course/shuffle.py
import random


def shuffled_order(seed: str, count: int) -> list[int]:
    """Return a permutation of range(count) that is reproducible from the seed."""
    order = list(range(count))
    random.Random(seed).shuffle(order)
    return order
```

```python
# backend/app/course/presenter.py
from app.content.models import (
    BuildSentenceExercise,
    ChooseFormExercise,
    Course,
    DialogReplyExercise,
    Exercise,
    MatchPairsExercise,
    TokenRef,
)
from app.course.shuffle import shuffled_order


def _word(course: Course, ref: TokenRef) -> dict:
    form = course.form(ref)
    return {"text": form.text, "translit": form.translit}


def build_sentence_tiles(course: Course, exercise: BuildSentenceExercise) -> list[TokenRef]:
    """The tile pool in the exact order the client will see it."""
    pool = list(exercise.solution) + list(exercise.distractors)
    return [pool[position] for position in shuffled_order(exercise.id, len(pool))]


def choose_form_options(course: Course, exercise: ChooseFormExercise) -> list[TokenRef]:
    lexeme_id, _ = exercise.answer
    pool = [exercise.answer] + [(lexeme_id, key) for key in exercise.distractor_forms]
    return [pool[position] for position in shuffled_order(exercise.id, len(pool))]


def match_pairs_sides(
    course: Course, exercise: MatchPairsExercise
) -> tuple[list[TokenRef], list[TokenRef]]:
    left_order = shuffled_order(exercise.id + ":l", len(exercise.pairs))
    right_order = shuffled_order(exercise.id + ":r", len(exercise.pairs))
    left = [exercise.pairs[position] for position in left_order]
    right = [exercise.pairs[position] for position in right_order]
    return left, right


def dialog_reply_options(course: Course, exercise: DialogReplyExercise) -> list[int]:
    """Original option indices in display order."""
    return shuffled_order(exercise.id, len(exercise.options))


def present_exercise(course: Course, exercise: Exercise) -> dict:
    """Render an exercise for the client. Never includes the solution."""
    base = {"id": exercise.id, "type": exercise.type, "prompt_de": exercise.prompt_de}

    if isinstance(exercise, BuildSentenceExercise):
        tiles = build_sentence_tiles(course, exercise)
        return base | {
            "tiles": [
                {"index": index, **_word(course, ref)} for index, ref in enumerate(tiles)
            ]
        }

    if isinstance(exercise, ChooseFormExercise):
        options = choose_form_options(course, exercise)
        return base | {
            "sentence": [None if ref is None else _word(course, ref) for ref in exercise.sentence],
            "options": [
                {"index": index, **_word(course, ref)} for index, ref in enumerate(options)
            ],
        }

    if isinstance(exercise, MatchPairsExercise):
        left, right = match_pairs_sides(course, exercise)
        return base | {
            "left": [{"index": index, **_word(course, ref)} for index, ref in enumerate(left)],
            "right": [
                {"index": index, "gloss_de": course.gloss(ref)} for index, ref in enumerate(right)
            ],
        }

    if isinstance(exercise, DialogReplyExercise):
        order = dialog_reply_options(course, exercise)
        options = []
        for display_index, original in enumerate(order):
            tokens = exercise.options[original].tokens
            options.append(
                {
                    "index": display_index,
                    "text": " ".join(course.form(ref).text for ref in tokens),
                    "translit": " ".join(course.form(ref).translit for ref in tokens),
                }
            )
        return base | {
            "tutor_line": [_word(course, ref) for ref in exercise.tutor_line],
            "options": options,
        }

    raise ValueError(f"Unbekannter Aufgabentyp: {exercise!r}")
```

Create `backend/app/course/__init__.py` as an empty file.

- [ ] **Step 4: Run presenter test to verify it passes**

Run: `cd backend && .venv/bin/pytest tests/test_course_presenter.py -v`
Expected: PASS (7 tests)

- [ ] **Step 5: Write the failing checker test**

```python
# backend/tests/test_course_checker.py
from app.content.loader import load_course
from app.course.checker import check_answer
from app.course.presenter import (
    build_sentence_tiles,
    choose_form_options,
    dialog_reply_options,
    match_pairs_sides,
)
from tests.content_factory import write_course


def _course(tmp_path):
    return load_course(write_course(tmp_path))


def test_build_sentence_accepts_correct_order(tmp_path):
    course = _course(tmp_path)
    exercise = course.units[1].exercises[0]
    tiles = build_sentence_tiles(course, exercise)
    indices = [tiles.index(ref) for ref in exercise.solution]
    result = check_answer(course, exercise, {"tile_indices": indices})
    assert result.correct is True
    assert result.solution_text == "я де́лаю"


def test_build_sentence_rejects_wrong_order(tmp_path):
    course = _course(tmp_path)
    exercise = course.units[1].exercises[0]
    tiles = build_sentence_tiles(course, exercise)
    indices = [tiles.index(ref) for ref in reversed(exercise.solution)]
    result = check_answer(course, exercise, {"tile_indices": indices})
    assert result.correct is False
    assert result.solution_text == "я де́лаю"


def test_build_sentence_rejects_extra_tile(tmp_path):
    course = _course(tmp_path)
    exercise = course.units[1].exercises[0]
    result = check_answer(course, exercise, {"tile_indices": [0, 1, 2]})
    assert result.correct is False


def test_build_sentence_reports_trained_forms(tmp_path):
    course = _course(tmp_path)
    exercise = course.units[1].exercises[0]
    tiles = build_sentence_tiles(course, exercise)
    indices = [tiles.index(ref) for ref in exercise.solution]
    result = check_answer(course, exercise, {"tile_indices": indices})
    assert result.trained_forms == [("ja", "nom"), ("delat", "prs.1sg")]


def test_choose_form_accepts_correct_option(tmp_path):
    course = _course(tmp_path)
    exercise = course.units[1].exercises[1]
    options = choose_form_options(course, exercise)
    result = check_answer(course, exercise, {"option_index": options.index(exercise.answer)})
    assert result.correct is True
    assert result.trained_forms == [("delat", "prs.1sg")]


def test_choose_form_wrong_option_explains_the_right_form(tmp_path):
    course = _course(tmp_path)
    exercise = course.units[1].exercises[1]
    options = choose_form_options(course, exercise)
    wrong = next(index for index, ref in enumerate(options) if ref != exercise.answer)
    result = check_answer(course, exercise, {"option_index": wrong})
    assert result.correct is False
    assert result.solution_text == "де́лаю"
    assert "де́лаю" in result.explanation_de


def test_match_pairs_accepts_correct_mapping(tmp_path):
    course = _course(tmp_path)
    exercise = course.units[1].exercises[2]
    left, right = match_pairs_sides(course, exercise)
    pairs = [[index, right.index(ref)] for index, ref in enumerate(left)]
    result = check_answer(course, exercise, {"pairs": pairs})
    assert result.correct is True


def test_match_pairs_rejects_swapped_mapping(tmp_path):
    course = _course(tmp_path)
    exercise = course.units[1].exercises[2]
    left, right = match_pairs_sides(course, exercise)
    pairs = [[index, (right.index(ref) + 1) % len(right)] for index, ref in enumerate(left)]
    result = check_answer(course, exercise, {"pairs": pairs})
    assert result.correct is False


def test_dialog_reply_accepts_correct_option(tmp_path):
    course = _course(tmp_path)
    exercise = course.units[1].exercises[3]
    order = dialog_reply_options(course, exercise)
    result = check_answer(
        course, exercise, {"option_index": order.index(exercise.correct_index)}
    )
    assert result.correct is True


def test_dialog_reply_wrong_option_returns_its_reason(tmp_path):
    course = _course(tmp_path)
    exercise = course.units[1].exercises[3]
    order = dialog_reply_options(course, exercise)
    wrong = next(i for i, original in enumerate(order) if original != exercise.correct_index)
    result = check_answer(course, exercise, {"option_index": wrong})
    assert result.correct is False
    assert result.explanation_de == "Das ist die Form für er/sie."


def test_out_of_range_index_is_wrong_not_an_error(tmp_path):
    course = _course(tmp_path)
    exercise = course.units[1].exercises[1]
    result = check_answer(course, exercise, {"option_index": 99})
    assert result.correct is False


def test_missing_submission_key_is_wrong_not_an_error(tmp_path):
    course = _course(tmp_path)
    exercise = course.units[1].exercises[0]
    assert check_answer(course, exercise, {}).correct is False
```

- [ ] **Step 6: Run test to verify it fails**

Run: `cd backend && .venv/bin/pytest tests/test_course_checker.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.course.checker'`

- [ ] **Step 7: Implement the checker**

```python
# backend/app/course/checker.py
from dataclasses import dataclass

from app.content.models import (
    BuildSentenceExercise,
    ChooseFormExercise,
    Course,
    DialogReplyExercise,
    Exercise,
    MatchPairsExercise,
    TokenRef,
)
from app.course.presenter import (
    build_sentence_tiles,
    choose_form_options,
    dialog_reply_options,
    match_pairs_sides,
)


@dataclass(frozen=True)
class CheckResult:
    correct: bool
    solution_text: str
    solution_translit: str
    explanation_de: str
    trained_forms: list[TokenRef]


def _render(course: Course, refs: list[TokenRef]) -> tuple[str, str]:
    return (
        " ".join(course.form(ref).text for ref in refs),
        " ".join(course.form(ref).translit for ref in refs),
    )


def _check_build_sentence(
    course: Course, exercise: BuildSentenceExercise, submission: dict
) -> CheckResult:
    tiles = build_sentence_tiles(course, exercise)
    indices = submission.get("tile_indices")
    chosen: list[TokenRef] = []
    if isinstance(indices, list) and all(
        isinstance(index, int) and 0 <= index < len(tiles) for index in indices
    ):
        chosen = [tiles[index] for index in indices]
    text, translit = _render(course, exercise.solution)
    correct = chosen == exercise.solution
    return CheckResult(
        correct=correct,
        solution_text=text,
        solution_translit=translit,
        explanation_de="" if correct else f"Richtig ist: {text}",
        trained_forms=list(exercise.solution),
    )


def _check_choose_form(
    course: Course, exercise: ChooseFormExercise, submission: dict
) -> CheckResult:
    options = choose_form_options(course, exercise)
    index = submission.get("option_index")
    chosen = options[index] if isinstance(index, int) and 0 <= index < len(options) else None
    text, translit = _render(course, [exercise.answer])
    correct = chosen == exercise.answer
    return CheckResult(
        correct=correct,
        solution_text=text,
        solution_translit=translit,
        explanation_de="" if correct else f"Hier passt die Form {text}.",
        trained_forms=[exercise.answer],
    )


def _check_match_pairs(
    course: Course, exercise: MatchPairsExercise, submission: dict
) -> CheckResult:
    left, right = match_pairs_sides(course, exercise)
    pairs = submission.get("pairs")
    correct = False
    if isinstance(pairs, list) and len(pairs) == len(left):
        correct = all(
            isinstance(pair, (list, tuple))
            and len(pair) == 2
            and isinstance(pair[0], int)
            and isinstance(pair[1], int)
            and 0 <= pair[0] < len(left)
            and 0 <= pair[1] < len(right)
            and course.gloss(left[pair[0]]) == course.gloss(right[pair[1]])
            for pair in pairs
        )
    text, translit = _render(course, exercise.pairs)
    return CheckResult(
        correct=correct,
        solution_text=text,
        solution_translit=translit,
        explanation_de="" if correct else "Nicht alle Paare stimmen.",
        trained_forms=list(exercise.pairs),
    )


def _check_dialog_reply(
    course: Course, exercise: DialogReplyExercise, submission: dict
) -> CheckResult:
    order = dialog_reply_options(course, exercise)
    index = submission.get("option_index")
    original = order[index] if isinstance(index, int) and 0 <= index < len(order) else None
    correct_option = exercise.options[exercise.correct_index]
    text, translit = _render(course, correct_option.tokens)
    correct = original == exercise.correct_index
    explanation = ""
    if not correct:
        explanation = (
            exercise.options[original].why_de
            if original is not None
            else f"Richtig ist: {text}"
        )
    return CheckResult(
        correct=correct,
        solution_text=text,
        solution_translit=translit,
        explanation_de=explanation,
        trained_forms=list(correct_option.tokens),
    )


def check_answer(course: Course, exercise: Exercise, submission: dict) -> CheckResult:
    """Grade a submission. Malformed input counts as a wrong answer, never an error."""
    if isinstance(exercise, BuildSentenceExercise):
        return _check_build_sentence(course, exercise, submission)
    if isinstance(exercise, ChooseFormExercise):
        return _check_choose_form(course, exercise, submission)
    if isinstance(exercise, MatchPairsExercise):
        return _check_match_pairs(course, exercise, submission)
    if isinstance(exercise, DialogReplyExercise):
        return _check_dialog_reply(course, exercise, submission)
    raise ValueError(f"Unbekannter Aufgabentyp: {exercise!r}")
```

- [ ] **Step 8: Run test to verify it passes**

Run: `cd backend && .venv/bin/pytest tests/test_course_checker.py -v`
Expected: PASS (12 tests)

- [ ] **Step 9: Commit**

```bash
git add backend/app/course backend/tests/test_course_presenter.py backend/tests/test_course_checker.py
git commit -m "feat: add exercise presentation and server-side answer checking"
```

---
## Task 5: Datenbank-Erweiterung, Migration und Fortschritts-Repositories

**Files:**
- Modify: `backend/app/db.py` (SCHEMA erweitern, `_ensure_profile_columns` ergänzen)
- Modify: `backend/app/repositories/profile_repo.py`
- Create: `backend/app/repositories/progress_repo.py`
- Create: `backend/app/repositories/lexeme_srs_repo.py`
- Test: `backend/tests/test_progress_repo.py`
- Test: `backend/tests/test_lexeme_srs_repo.py`
- Test: `backend/tests/test_db_migration.py`

**Interfaces:**
- Consumes: `get_connection`, `init_db` aus `app.db`
- Produces:
  - `Profile(language, cefr_level, created_at, show_transliteration: bool, placement_unit: int | None)` und `update_profile(conn, *, language=None, cefr_level=None, show_transliteration=None, placement_unit=None) -> Profile` aus `app.repositories.profile_repo`
  - `UnitProgress(unit_id, status, correct_count, total_count, completed_at)`, `record_attempt(conn, *, unit_id, exercise_id, correct, answer_json)`, `bump_progress(conn, *, unit_id, correct) -> UnitProgress`, `complete_unit(conn, *, unit_id) -> UnitProgress`, `get_progress(conn, unit_id) -> UnitProgress | None`, `all_progress(conn) -> dict[int, UnitProgress]`, `attempt_count(conn, unit_id) -> int` aus `app.repositories.progress_repo`
  - `SrsState(lexeme_id, form_key, interval_days, ease_factor, repetitions, due_date)`, `get_state(conn, *, lexeme_id, form_key) -> SrsState | None`, `upsert_state(conn, state: SrsState) -> None`, `due_states(conn, *, today: str, limit: int = 20) -> list[SrsState]` aus `app.repositories.lexeme_srs_repo`

- [ ] **Step 1: Write the failing migration test**

```python
# backend/tests/test_db_migration.py
import sqlite3

from app.db import get_connection, init_db

OLD_PROFILE_SCHEMA = """
CREATE TABLE profile (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    language TEXT NOT NULL,
    cefr_level TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""


def _columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}


def test_init_db_creates_new_tables(tmp_path):
    path = str(tmp_path / "new.db")
    init_db(path)
    conn = get_connection(path)
    names = {
        row["name"]
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }
    assert {"unit_progress", "exercise_attempts", "lexeme_srs", "screening_results"} <= names
    conn.close()


def test_init_db_adds_missing_profile_columns_to_old_database(tmp_path):
    path = str(tmp_path / "old.db")
    legacy = sqlite3.connect(path)
    legacy.executescript(OLD_PROFILE_SCHEMA)
    legacy.execute(
        "INSERT INTO profile (id, language, cefr_level, created_at) VALUES (1, 'english', 'A2', '2026-01-01')"
    )
    legacy.commit()
    legacy.close()

    init_db(path)

    conn = get_connection(path)
    assert {"show_transliteration", "placement_unit"} <= _columns(conn, "profile")
    row = conn.execute("SELECT * FROM profile WHERE id = 1").fetchone()
    assert row["cefr_level"] == "A2"
    assert row["show_transliteration"] == 1
    assert row["placement_unit"] is None
    conn.close()


def test_init_db_is_idempotent(tmp_path):
    path = str(tmp_path / "twice.db")
    init_db(path)
    init_db(path)
    conn = get_connection(path)
    assert len(_columns(conn, "profile")) == 6
    conn.close()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && .venv/bin/pytest tests/test_db_migration.py -v`
Expected: FAIL — `unit_progress` fehlt in den Tabellennamen

- [ ] **Step 3: Extend the schema and add the migration**

Append to `SCHEMA` in `backend/app/db.py`:

```sql
CREATE TABLE IF NOT EXISTS unit_progress (
    unit_id       INTEGER PRIMARY KEY,
    status        TEXT NOT NULL,
    correct_count INTEGER NOT NULL DEFAULT 0,
    total_count   INTEGER NOT NULL DEFAULT 0,
    completed_at  TEXT
);

CREATE TABLE IF NOT EXISTS exercise_attempts (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    unit_id     INTEGER NOT NULL,
    exercise_id TEXT NOT NULL,
    correct     INTEGER NOT NULL,
    answer_json TEXT NOT NULL,
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS lexeme_srs (
    lexeme_id     TEXT NOT NULL,
    form_key      TEXT NOT NULL,
    interval_days REAL NOT NULL DEFAULT 0,
    ease_factor   REAL NOT NULL DEFAULT 2.5,
    repetitions   INTEGER NOT NULL DEFAULT 0,
    due_date      TEXT NOT NULL,
    PRIMARY KEY (lexeme_id, form_key)
);

CREATE TABLE IF NOT EXISTS screening_results (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    answers_json   TEXT NOT NULL,
    placement_unit INTEGER NOT NULL,
    created_at     TEXT NOT NULL
);
```

Replace `init_db` in `backend/app/db.py` with:

```python
PROFILE_COLUMNS = {
    "show_transliteration": "INTEGER NOT NULL DEFAULT 1",
    "placement_unit": "INTEGER",
}


def _ensure_profile_columns(conn: sqlite3.Connection) -> None:
    """Add columns introduced after the first release to an existing profile table."""
    existing = {row["name"] for row in conn.execute("PRAGMA table_info(profile)")}
    for name, definition in PROFILE_COLUMNS.items():
        if name not in existing:
            conn.execute(f"ALTER TABLE profile ADD COLUMN {name} {definition}")


def init_db(db_path: str) -> None:
    conn = get_connection(db_path)
    try:
        conn.executescript(SCHEMA)
        _ensure_profile_columns(conn)
        conn.commit()
    finally:
        conn.close()
```

Also add the two new columns to the `CREATE TABLE IF NOT EXISTS profile` statement in `SCHEMA` so fresh databases get them directly:

```sql
CREATE TABLE IF NOT EXISTS profile (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    language TEXT NOT NULL,
    cefr_level TEXT NOT NULL,
    created_at TEXT NOT NULL,
    show_transliteration INTEGER NOT NULL DEFAULT 1,
    placement_unit INTEGER
);
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && .venv/bin/pytest tests/test_db_migration.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Write the failing profile test**

Append to `backend/tests/test_profile_repo.py`:

```python
def test_profile_defaults_show_transliteration_on(conn):
    profile = profile_repo.get_or_create_profile(conn, default_language="russian")
    assert profile.show_transliteration is True
    assert profile.placement_unit is None


def test_update_profile_toggles_transliteration(conn):
    profile_repo.get_or_create_profile(conn, default_language="russian")
    updated = profile_repo.update_profile(conn, show_transliteration=False)
    assert updated.show_transliteration is False
    assert profile_repo.get_or_create_profile(conn, "russian").show_transliteration is False


def test_update_profile_stores_placement_unit(conn):
    profile_repo.get_or_create_profile(conn, default_language="russian")
    assert profile_repo.update_profile(conn, placement_unit=7).placement_unit == 7
```

- [ ] **Step 6: Extend the profile repository**

Rewrite `backend/app/repositories/profile_repo.py`:

```python
import datetime as dt
from dataclasses import dataclass
from sqlite3 import Connection, Row

SELECT_COLUMNS = "language, cefr_level, created_at, show_transliteration, placement_unit"


@dataclass
class Profile:
    language: str
    cefr_level: str
    created_at: str
    show_transliteration: bool = True
    placement_unit: int | None = None


def _row_to_profile(row: Row) -> Profile:
    return Profile(
        language=row["language"],
        cefr_level=row["cefr_level"],
        created_at=row["created_at"],
        show_transliteration=bool(row["show_transliteration"]),
        placement_unit=row["placement_unit"],
    )


def get_or_create_profile(conn: Connection, default_language: str) -> Profile:
    row = conn.execute(f"SELECT {SELECT_COLUMNS} FROM profile WHERE id = 1").fetchone()
    if row is not None:
        return _row_to_profile(row)

    created_at = dt.datetime.now(dt.timezone.utc).isoformat()
    conn.execute(
        "INSERT INTO profile (id, language, cefr_level, created_at, show_transliteration, placement_unit)"
        " VALUES (1, ?, ?, ?, 1, NULL)",
        (default_language, "UNPLACED", created_at),
    )
    conn.commit()
    return Profile(language=default_language, cefr_level="UNPLACED", created_at=created_at)


def update_profile(
    conn: Connection,
    *,
    language: str | None = None,
    cefr_level: str | None = None,
    show_transliteration: bool | None = None,
    placement_unit: int | None = None,
) -> Profile:
    current = get_or_create_profile(conn, default_language=language or "russian")
    new = Profile(
        language=language if language is not None else current.language,
        cefr_level=cefr_level if cefr_level is not None else current.cefr_level,
        created_at=current.created_at,
        show_transliteration=(
            show_transliteration
            if show_transliteration is not None
            else current.show_transliteration
        ),
        placement_unit=placement_unit if placement_unit is not None else current.placement_unit,
    )
    conn.execute(
        "UPDATE profile SET language = ?, cefr_level = ?, show_transliteration = ?,"
        " placement_unit = ? WHERE id = 1",
        (new.language, new.cefr_level, int(new.show_transliteration), new.placement_unit),
    )
    conn.commit()
    return new
```

- [ ] **Step 7: Run the profile tests**

Run: `cd backend && .venv/bin/pytest tests/test_profile_repo.py -v`
Expected: PASS — auch die bereits vorhandenen Tests

- [ ] **Step 8: Write the failing progress-repository test**

```python
# backend/tests/test_progress_repo.py
from app.repositories import progress_repo


def test_bump_progress_creates_row_on_first_attempt(conn):
    progress = progress_repo.bump_progress(conn, unit_id=3, correct=True)
    assert progress.unit_id == 3
    assert progress.status == "in_progress"
    assert (progress.correct_count, progress.total_count) == (1, 1)


def test_bump_progress_counts_wrong_answers_in_total_only(conn):
    progress_repo.bump_progress(conn, unit_id=3, correct=True)
    progress = progress_repo.bump_progress(conn, unit_id=3, correct=False)
    assert (progress.correct_count, progress.total_count) == (1, 2)


def test_complete_unit_sets_status_and_timestamp(conn):
    progress_repo.bump_progress(conn, unit_id=3, correct=True)
    progress = progress_repo.complete_unit(conn, unit_id=3)
    assert progress.status == "completed"
    assert progress.completed_at is not None


def test_get_progress_returns_none_for_untouched_unit(conn):
    assert progress_repo.get_progress(conn, 99) is None


def test_all_progress_is_keyed_by_unit_id(conn):
    progress_repo.bump_progress(conn, unit_id=1, correct=True)
    progress_repo.bump_progress(conn, unit_id=2, correct=False)
    assert set(progress_repo.all_progress(conn)) == {1, 2}


def test_record_attempt_is_queryable(conn):
    progress_repo.record_attempt(
        conn, unit_id=1, exercise_id="1-1", correct=False, answer_json='{"tile_indices":[1,0]}'
    )
    progress_repo.record_attempt(
        conn, unit_id=1, exercise_id="1-2", correct=True, answer_json='{"option_index":0}'
    )
    assert progress_repo.attempt_count(conn, 1) == 2
```

- [ ] **Step 9: Implement the progress repository**

```python
# backend/app/repositories/progress_repo.py
import datetime as dt
from dataclasses import dataclass
from sqlite3 import Connection, Row


@dataclass
class UnitProgress:
    unit_id: int
    status: str
    correct_count: int
    total_count: int
    completed_at: str | None


def _row(row: Row) -> UnitProgress:
    return UnitProgress(
        unit_id=row["unit_id"],
        status=row["status"],
        correct_count=row["correct_count"],
        total_count=row["total_count"],
        completed_at=row["completed_at"],
    )


def get_progress(conn: Connection, unit_id: int) -> UnitProgress | None:
    row = conn.execute("SELECT * FROM unit_progress WHERE unit_id = ?", (unit_id,)).fetchone()
    return _row(row) if row else None


def all_progress(conn: Connection) -> dict[int, UnitProgress]:
    return {row["unit_id"]: _row(row) for row in conn.execute("SELECT * FROM unit_progress")}


def bump_progress(conn: Connection, *, unit_id: int, correct: bool) -> UnitProgress:
    """Count one answered exercise towards the unit's progress."""
    conn.execute(
        "INSERT INTO unit_progress (unit_id, status, correct_count, total_count)"
        " VALUES (?, 'in_progress', 0, 0)"
        " ON CONFLICT(unit_id) DO NOTHING",
        (unit_id,),
    )
    conn.execute(
        "UPDATE unit_progress SET correct_count = correct_count + ?, total_count = total_count + 1"
        " WHERE unit_id = ?",
        (1 if correct else 0, unit_id),
    )
    conn.commit()
    progress = get_progress(conn, unit_id)
    assert progress is not None
    return progress


def complete_unit(conn: Connection, *, unit_id: int) -> UnitProgress:
    completed_at = dt.datetime.now(dt.timezone.utc).isoformat()
    conn.execute(
        "INSERT INTO unit_progress (unit_id, status, correct_count, total_count, completed_at)"
        " VALUES (?, 'completed', 0, 0, ?)"
        " ON CONFLICT(unit_id) DO UPDATE SET status = 'completed', completed_at = excluded.completed_at",
        (unit_id, completed_at),
    )
    conn.commit()
    progress = get_progress(conn, unit_id)
    assert progress is not None
    return progress


def record_attempt(
    conn: Connection, *, unit_id: int, exercise_id: str, correct: bool, answer_json: str
) -> None:
    conn.execute(
        "INSERT INTO exercise_attempts (unit_id, exercise_id, correct, answer_json, created_at)"
        " VALUES (?, ?, ?, ?, ?)",
        (unit_id, exercise_id, int(correct), answer_json, dt.datetime.now(dt.timezone.utc).isoformat()),
    )
    conn.commit()


def attempt_count(conn: Connection, unit_id: int) -> int:
    row = conn.execute(
        "SELECT COUNT(*) AS n FROM exercise_attempts WHERE unit_id = ?", (unit_id,)
    ).fetchone()
    return int(row["n"])
```

- [ ] **Step 10: Run test to verify it passes**

Run: `cd backend && .venv/bin/pytest tests/test_progress_repo.py -v`
Expected: PASS (6 tests)

- [ ] **Step 11: Write the failing SRS-repository test**

```python
# backend/tests/test_lexeme_srs_repo.py
from app.repositories import lexeme_srs_repo
from app.repositories.lexeme_srs_repo import SrsState


def _state(lexeme_id="delat", form_key="prs.1sg", due_date="2026-09-01") -> SrsState:
    return SrsState(
        lexeme_id=lexeme_id,
        form_key=form_key,
        interval_days=1.0,
        ease_factor=2.5,
        repetitions=1,
        due_date=due_date,
    )


def test_get_state_returns_none_when_unknown(conn):
    assert lexeme_srs_repo.get_state(conn, lexeme_id="delat", form_key="prs.1sg") is None


def test_upsert_then_get_round_trips(conn):
    lexeme_srs_repo.upsert_state(conn, _state())
    stored = lexeme_srs_repo.get_state(conn, lexeme_id="delat", form_key="prs.1sg")
    assert stored == _state()


def test_upsert_replaces_existing_state(conn):
    lexeme_srs_repo.upsert_state(conn, _state())
    lexeme_srs_repo.upsert_state(conn, _state(due_date="2026-12-24"))
    stored = lexeme_srs_repo.get_state(conn, lexeme_id="delat", form_key="prs.1sg")
    assert stored.due_date == "2026-12-24"


def test_forms_of_same_lexeme_are_tracked_separately(conn):
    lexeme_srs_repo.upsert_state(conn, _state(form_key="prs.1sg"))
    lexeme_srs_repo.upsert_state(conn, _state(form_key="prs.3sg"))
    assert len(lexeme_srs_repo.due_states(conn, today="2026-09-02")) == 2


def test_due_states_excludes_future_dates(conn):
    lexeme_srs_repo.upsert_state(conn, _state(due_date="2026-09-01"))
    lexeme_srs_repo.upsert_state(conn, _state(form_key="prs.3sg", due_date="2026-09-30"))
    due = lexeme_srs_repo.due_states(conn, today="2026-09-02")
    assert [state.form_key for state in due] == ["prs.1sg"]


def test_due_states_respects_limit(conn):
    for index in range(5):
        lexeme_srs_repo.upsert_state(conn, _state(lexeme_id=f"l{index}"))
    assert len(lexeme_srs_repo.due_states(conn, today="2026-09-02", limit=3)) == 3
```

- [ ] **Step 12: Implement the SRS repository**

```python
# backend/app/repositories/lexeme_srs_repo.py
from dataclasses import dataclass
from sqlite3 import Connection, Row


@dataclass
class SrsState:
    lexeme_id: str
    form_key: str
    interval_days: float
    ease_factor: float
    repetitions: int
    due_date: str


def _row(row: Row) -> SrsState:
    return SrsState(
        lexeme_id=row["lexeme_id"],
        form_key=row["form_key"],
        interval_days=row["interval_days"],
        ease_factor=row["ease_factor"],
        repetitions=row["repetitions"],
        due_date=row["due_date"],
    )


def get_state(conn: Connection, *, lexeme_id: str, form_key: str) -> SrsState | None:
    row = conn.execute(
        "SELECT * FROM lexeme_srs WHERE lexeme_id = ? AND form_key = ?", (lexeme_id, form_key)
    ).fetchone()
    return _row(row) if row else None


def upsert_state(conn: Connection, state: SrsState) -> None:
    conn.execute(
        "INSERT INTO lexeme_srs (lexeme_id, form_key, interval_days, ease_factor, repetitions, due_date)"
        " VALUES (?, ?, ?, ?, ?, ?)"
        " ON CONFLICT(lexeme_id, form_key) DO UPDATE SET"
        " interval_days = excluded.interval_days, ease_factor = excluded.ease_factor,"
        " repetitions = excluded.repetitions, due_date = excluded.due_date",
        (
            state.lexeme_id,
            state.form_key,
            state.interval_days,
            state.ease_factor,
            state.repetitions,
            state.due_date,
        ),
    )
    conn.commit()


def due_states(conn: Connection, *, today: str, limit: int = 20) -> list[SrsState]:
    rows = conn.execute(
        "SELECT * FROM lexeme_srs WHERE due_date <= ? ORDER BY due_date, lexeme_id, form_key LIMIT ?",
        (today, limit),
    ).fetchall()
    return [_row(row) for row in rows]
```

- [ ] **Step 13: Run the full backend suite**

Run: `cd backend && .venv/bin/pytest -v`
Expected: PASS — alle bestehenden Tests bleiben grün

- [ ] **Step 14: Commit**

```bash
git add backend/app/db.py backend/app/repositories backend/tests/test_db_migration.py backend/tests/test_progress_repo.py backend/tests/test_lexeme_srs_repo.py backend/tests/test_profile_repo.py
git commit -m "feat: add progress and word-form SRS persistence"
```

---
## Task 6: Kurs-Service und Wiederholungsrunden

**Files:**
- Create: `backend/app/course/service.py`
- Create: `backend/app/course/review.py`
- Modify: `backend/app/repositories/progress_repo.py` (Funktion `correct_exercise_ids` ergänzen)
- Test: `backend/tests/test_course_service.py`
- Test: `backend/tests/test_course_review.py`

**Interfaces:**
- Consumes: `check_answer`, `CheckResult` aus `app.course.checker`; `present_exercise`, `match_pairs_sides` aus `app.course.presenter`; `shuffled_order` aus `app.course.shuffle`; `sm2_update` aus `app.srs.sm2`; `progress_repo`, `lexeme_srs_repo`
- Produces:
  - `correct_exercise_ids(conn, unit_id) -> set[str]` in `app.repositories.progress_repo`
  - `submit_answer(conn, course, *, unit_id, exercise_id, submission, today=None) -> AnswerOutcome` und `AnswerOutcome(correct, solution_text, solution_translit, explanation_de, unit_completed, correct_count, total_count)` aus `app.course.service`
  - `unit_payload(course, conn, unit_id) -> dict` aus `app.course.service`
  - `course_overview(course, conn) -> dict` aus `app.course.service`
  - `build_review_round(conn, course, *, today, size=5) -> dict` und `grade_review_round(conn, course, *, today, submission, size=5) -> dict` aus `app.course.review`

Eine Einheit gilt als abgeschlossen, sobald **jede** ihrer Aufgaben mindestens einmal richtig beantwortet wurde. Falsche Antworten kosten nichts außer einem weiteren Versuch — das ist für Anfänger die freundlichere Regel als ein Herzchen-System.

- [ ] **Step 1: Write the failing service test**

```python
# backend/tests/test_course_service.py
import pytest

from app.content.loader import load_course
from app.course import service
from app.course.presenter import build_sentence_tiles, choose_form_options
from app.repositories import lexeme_srs_repo, progress_repo
from tests.content_factory import write_course


@pytest.fixture
def course(tmp_path):
    return load_course(write_course(tmp_path))


def _correct_build_submission(course):
    exercise = course.units[1].exercises[0]
    tiles = build_sentence_tiles(course, exercise)
    return exercise.id, {"tile_indices": [tiles.index(ref) for ref in exercise.solution]}


def test_correct_answer_reports_success_and_counts(conn, course):
    exercise_id, submission = _correct_build_submission(course)
    outcome = service.submit_answer(
        conn, course, unit_id=1, exercise_id=exercise_id, submission=submission
    )
    assert outcome.correct is True
    assert (outcome.correct_count, outcome.total_count) == (1, 1)


def test_wrong_answer_returns_solution_and_explanation(conn, course):
    outcome = service.submit_answer(
        conn, course, unit_id=1, exercise_id="1-1", submission={"tile_indices": [0]}
    )
    assert outcome.correct is False
    assert outcome.solution_text == "я де́лаю"
    assert outcome.explanation_de


def test_answer_is_recorded_as_attempt(conn, course):
    service.submit_answer(
        conn, course, unit_id=1, exercise_id="1-1", submission={"tile_indices": [0]}
    )
    assert progress_repo.attempt_count(conn, 1) == 1


def test_correct_answer_schedules_trained_forms_for_review(conn, course):
    exercise_id, submission = _correct_build_submission(course)
    service.submit_answer(
        conn, course, unit_id=1, exercise_id=exercise_id, submission=submission, today="2026-09-04"
    )
    state = lexeme_srs_repo.get_state(conn, lexeme_id="delat", form_key="prs.1sg")
    assert state is not None
    assert state.repetitions == 1
    assert state.due_date > "2026-09-04"


def test_wrong_answer_makes_trained_forms_due_again_immediately(conn, course):
    service.submit_answer(
        conn, course, unit_id=1, exercise_id="1-1", submission={"tile_indices": [0]}, today="2026-09-04"
    )
    state = lexeme_srs_repo.get_state(conn, lexeme_id="delat", form_key="prs.1sg")
    assert state.repetitions == 0
    assert state.due_date == "2026-09-05"


def test_unit_completes_only_after_every_exercise_was_right_once(conn, course):
    unit = course.units[1]
    outcomes = []
    for exercise in unit.exercises:
        submission = _submission_for(course, exercise)
        outcomes.append(
            service.submit_answer(
                conn, course, unit_id=1, exercise_id=exercise.id, submission=submission
            )
        )
    assert [outcome.unit_completed for outcome in outcomes] == [False, False, False, True]
    assert progress_repo.get_progress(conn, 1).status == "completed"


def _submission_for(course, exercise):
    from app.course.presenter import dialog_reply_options, match_pairs_sides

    if exercise.type == "build_sentence":
        tiles = build_sentence_tiles(course, exercise)
        return {"tile_indices": [tiles.index(ref) for ref in exercise.solution]}
    if exercise.type == "choose_form":
        options = choose_form_options(course, exercise)
        return {"option_index": options.index(exercise.answer)}
    if exercise.type == "match_pairs":
        left, right = match_pairs_sides(course, exercise)
        return {"pairs": [[index, right.index(ref)] for index, ref in enumerate(left)]}
    order = dialog_reply_options(course, exercise)
    return {"option_index": order.index(exercise.correct_index)}


def test_unknown_exercise_id_raises_key_error(conn, course):
    with pytest.raises(KeyError):
        service.submit_answer(conn, course, unit_id=1, exercise_id="nope", submission={})


def test_unit_payload_contains_rule_and_exercises_without_solutions(conn, course):
    payload = service.unit_payload(course, conn, unit_id=1)
    assert payload["grammar_focus"]["explanation_de"]
    assert len(payload["exercises"]) == 4
    assert all("solution" not in exercise for exercise in payload["exercises"])


def test_course_overview_groups_units_by_stage(conn, course):
    overview = service.course_overview(course, conn)
    stages = {stage["stage"] for stage in overview["stages"]}
    assert stages == {0}
    assert overview["stages"][0]["units"][0]["status"] == "not_started"


def test_course_overview_reflects_progress(conn, course):
    exercise_id, submission = _correct_build_submission(course)
    service.submit_answer(
        conn, course, unit_id=1, exercise_id=exercise_id, submission=submission
    )
    overview = service.course_overview(course, conn)
    assert overview["stages"][0]["units"][0]["status"] == "in_progress"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && .venv/bin/pytest tests/test_course_service.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.course.service'`

- [ ] **Step 3: Add `correct_exercise_ids` to the progress repository**

```python
# append to backend/app/repositories/progress_repo.py
def correct_exercise_ids(conn: Connection, unit_id: int) -> set[str]:
    """Exercise ids of this unit that were answered correctly at least once."""
    rows = conn.execute(
        "SELECT DISTINCT exercise_id FROM exercise_attempts WHERE unit_id = ? AND correct = 1",
        (unit_id,),
    ).fetchall()
    return {row["exercise_id"] for row in rows}
```

- [ ] **Step 4: Implement the course service**

```python
# backend/app/course/service.py
import datetime as dt
import json
from dataclasses import dataclass
from sqlite3 import Connection

from app.content.models import Course, TokenRef
from app.course.checker import check_answer
from app.course.presenter import present_exercise
from app.repositories import lexeme_srs_repo, progress_repo
from app.repositories.lexeme_srs_repo import SrsState
from app.srs.sm2 import sm2_update


@dataclass(frozen=True)
class AnswerOutcome:
    correct: bool
    solution_text: str
    solution_translit: str
    explanation_de: str
    unit_completed: bool
    correct_count: int
    total_count: int


def _today(today: str | None) -> str:
    return today or dt.date.today().isoformat()


def schedule_form(conn: Connection, ref: TokenRef, *, correct: bool, today: str) -> None:
    """Advance the SM-2 state of a single word form."""
    lexeme_id, form_key = ref
    state = lexeme_srs_repo.get_state(conn, lexeme_id=lexeme_id, form_key=form_key)
    result = sm2_update(
        correct=correct,
        repetitions=state.repetitions if state else 0,
        ease_factor=state.ease_factor if state else 2.5,
        interval_days=state.interval_days if state else 0.0,
    )
    due = dt.date.fromisoformat(today) + dt.timedelta(days=max(result.interval_days, 1))
    lexeme_srs_repo.upsert_state(
        conn,
        SrsState(
            lexeme_id=lexeme_id,
            form_key=form_key,
            interval_days=result.interval_days,
            ease_factor=result.ease_factor,
            repetitions=result.repetitions,
            due_date=due.isoformat(),
        ),
    )


def submit_answer(
    conn: Connection,
    course: Course,
    *,
    unit_id: int,
    exercise_id: str,
    submission: dict,
    today: str | None = None,
) -> AnswerOutcome:
    unit = course.units[unit_id]
    exercise = next((item for item in unit.exercises if item.id == exercise_id), None)
    if exercise is None:
        raise KeyError(f"Aufgabe {exercise_id!r} gehört nicht zu Einheit {unit_id}")

    result = check_answer(course, exercise, submission)
    progress_repo.record_attempt(
        conn,
        unit_id=unit_id,
        exercise_id=exercise_id,
        correct=result.correct,
        answer_json=json.dumps(submission, ensure_ascii=False),
    )
    progress = progress_repo.bump_progress(conn, unit_id=unit_id, correct=result.correct)

    day = _today(today)
    for ref in result.trained_forms:
        schedule_form(conn, ref, correct=result.correct, today=day)

    solved = progress_repo.correct_exercise_ids(conn, unit_id)
    completed = solved >= {item.id for item in unit.exercises}
    if completed and progress.status != "completed":
        progress = progress_repo.complete_unit(conn, unit_id=unit_id)

    return AnswerOutcome(
        correct=result.correct,
        solution_text=result.solution_text,
        solution_translit=result.solution_translit,
        explanation_de=result.explanation_de,
        unit_completed=completed,
        correct_count=progress.correct_count,
        total_count=progress.total_count,
    )


def unit_payload(course: Course, conn: Connection, unit_id: int) -> dict:
    unit = course.units[unit_id]
    solved = progress_repo.correct_exercise_ids(conn, unit_id)
    return {
        "id": unit.id,
        "stage": unit.stage,
        "title_de": unit.title_de,
        "scenario_de": unit.scenario_de,
        "grammar_focus": {
            "id": unit.grammar_focus.id,
            "title_de": unit.grammar_focus.title_de,
            "explanation_de": unit.grammar_focus.explanation_de,
        },
        "solved_exercise_ids": sorted(solved),
        "exercises": [present_exercise(course, exercise) for exercise in unit.exercises],
    }


def course_overview(course: Course, conn: Connection) -> dict:
    progress = progress_repo.all_progress(conn)
    stages: dict[int, list[dict]] = {}
    for unit in course.ordered_units():
        entry = progress.get(unit.id)
        stages.setdefault(unit.stage, []).append(
            {
                "id": unit.id,
                "title_de": unit.title_de,
                "scenario_de": unit.scenario_de,
                "status": entry.status if entry else "not_started",
                "correct_count": entry.correct_count if entry else 0,
                "exercise_count": len(unit.exercises),
            }
        )
    return {
        "stages": [
            {"stage": stage, "units": units} for stage, units in sorted(stages.items())
        ]
    }
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd backend && .venv/bin/pytest tests/test_course_service.py -v`
Expected: PASS (10 tests)

- [ ] **Step 6: Write the failing review test**

```python
# backend/tests/test_course_review.py
import pytest

from app.content.loader import load_course
from app.course import review
from app.repositories import lexeme_srs_repo
from app.repositories.lexeme_srs_repo import SrsState
from tests.content_factory import write_course

TODAY = "2026-09-10"


@pytest.fixture
def course(tmp_path):
    return load_course(write_course(tmp_path))


def _due(conn, lexeme_id, form_key, due_date="2026-09-01"):
    lexeme_srs_repo.upsert_state(
        conn,
        SrsState(
            lexeme_id=lexeme_id,
            form_key=form_key,
            interval_days=1.0,
            ease_factor=2.5,
            repetitions=1,
            due_date=due_date,
        ),
    )


def test_empty_round_when_nothing_is_due(conn, course):
    assert review.build_review_round(conn, course, today=TODAY)["left"] == []


def test_round_shows_due_forms_and_glosses(conn, course):
    _due(conn, "delat", "prs.1sg")
    _due(conn, "ja", "nom")
    payload = review.build_review_round(conn, course, today=TODAY)
    assert {item["text"] for item in payload["left"]} == {"де́лаю", "я"}
    assert {item["gloss_de"] for item in payload["right"]} == {"machen, tun", "ich"}


def test_round_skips_forms_that_are_no_longer_in_the_lexicon(conn, course):
    _due(conn, "gone", "nom")
    _due(conn, "ja", "nom")
    payload = review.build_review_round(conn, course, today=TODAY)
    assert len(payload["left"]) == 1


def test_correct_round_marks_every_form_as_passed(conn, course):
    _due(conn, "delat", "prs.1sg")
    _due(conn, "ja", "nom")
    payload = review.build_review_round(conn, course, today=TODAY)
    pairs = [
        [item["index"], next(
            other["index"] for other in payload["right"]
            if other["gloss_de"] == course.gloss(tuple(item["ref"].split(":")))
        )]
        for item in payload["left"]
    ]
    result = review.grade_review_round(conn, course, today=TODAY, submission={"pairs": pairs})
    assert result["correct_count"] == 2
    assert lexeme_srs_repo.get_state(conn, lexeme_id="ja", form_key="nom").due_date > TODAY


def test_wrong_pair_reschedules_only_that_form(conn, course):
    _due(conn, "delat", "prs.1sg")
    _due(conn, "ja", "nom")
    payload = review.build_review_round(conn, course, today=TODAY)
    swapped = [[item["index"], (index + 1) % len(payload["right"])]
               for index, item in enumerate(payload["left"])]
    result = review.grade_review_round(conn, course, today=TODAY, submission={"pairs": swapped})
    assert result["correct_count"] < 2


def test_round_size_is_capped(conn, course):
    for index in range(9):
        _due(conn, "delat", "prs.1sg" if index == 0 else "prs.2sg")
        _due(conn, "ja", "nom")
    assert len(review.build_review_round(conn, course, today=TODAY, size=2)["left"]) == 2
```

- [ ] **Step 7: Implement the review module**

```python
# backend/app/course/review.py
from sqlite3 import Connection

from app.content.models import Course, TokenRef
from app.course.service import schedule_form
from app.course.shuffle import shuffled_order
from app.repositories import lexeme_srs_repo


def _due_refs(conn: Connection, course: Course, *, today: str, size: int) -> list[TokenRef]:
    """Due word forms that still exist in the lexicon, in a stable order."""
    refs: list[TokenRef] = []
    for state in lexeme_srs_repo.due_states(conn, today=today, limit=size * 3):
        lexeme = course.lexemes.get(state.lexeme_id)
        if lexeme is None or state.form_key not in lexeme.forms:
            continue
        refs.append((state.lexeme_id, state.form_key))
        if len(refs) == size:
            break
    return refs


def build_review_round(conn: Connection, course: Course, *, today: str, size: int = 5) -> dict:
    """One matching round over the forms that are due today."""
    refs = _due_refs(conn, course, today=today, size=size)
    if not refs:
        return {"left": [], "right": []}

    right_order = shuffled_order(f"review:{today}", len(refs))
    left = [
        {
            "index": index,
            "ref": f"{ref[0]}:{ref[1]}",
            "text": course.form(ref).text,
            "translit": course.form(ref).translit,
        }
        for index, ref in enumerate(refs)
    ]
    right = [
        {"index": index, "gloss_de": course.gloss(refs[position])}
        for index, position in enumerate(right_order)
    ]
    return {"left": left, "right": right}


def grade_review_round(
    conn: Connection, course: Course, *, today: str, submission: dict, size: int = 5
) -> dict:
    """Grade a round rebuilt from the same due query, then reschedule each form."""
    refs = _due_refs(conn, course, today=today, size=size)
    right_order = shuffled_order(f"review:{today}", len(refs))
    chosen: dict[int, int] = {}
    for pair in submission.get("pairs", []):
        if (
            isinstance(pair, (list, tuple))
            and len(pair) == 2
            and isinstance(pair[0], int)
            and isinstance(pair[1], int)
            and 0 <= pair[0] < len(refs)
            and 0 <= pair[1] < len(right_order)
        ):
            chosen[pair[0]] = pair[1]

    correct_count = 0
    results = []
    for index, ref in enumerate(refs):
        picked = chosen.get(index)
        correct = picked is not None and right_order[picked] == index
        correct_count += int(correct)
        schedule_form(conn, ref, correct=correct, today=today)
        results.append(
            {
                "ref": f"{ref[0]}:{ref[1]}",
                "correct": correct,
                "gloss_de": course.gloss(ref),
                "text": course.form(ref).text,
            }
        )
    return {"correct_count": correct_count, "total_count": len(refs), "results": results}
```

- [ ] **Step 8: Run test to verify it passes**

Run: `cd backend && .venv/bin/pytest tests/test_course_review.py -v`
Expected: PASS (6 tests)

- [ ] **Step 9: Commit**

```bash
git add backend/app/course/service.py backend/app/course/review.py backend/app/repositories/progress_repo.py backend/tests/test_course_service.py backend/tests/test_course_review.py
git commit -m "feat: add course progression service and review rounds"
```

---
## Task 7: Adaptive Klick-Einstufung

**Files:**
- Create: `backend/app/screening/__init__.py`
- Create: `backend/app/screening/service.py`
- Test: `backend/tests/test_screening_service.py`

**Interfaces:**
- Consumes: `Course`, `ScreeningProbe` aus `app.content.models`; `update_profile` aus `app.repositories.profile_repo`
- Produces: `probe_payload(course, index) -> dict`, `next_step(course, answers: list[int]) -> dict`, `placement_unit_for(course, answers: list[int]) -> int`, `finish_screening(conn, course, answers: list[int]) -> int` aus `app.screening.service`

Das Screening ist zustandslos: der Client schickt bei jeder Antwort die komplette Liste seiner bisherigen Auswahlen zurück, der Server rechnet daraus Abbruch und Einstufung neu. Kein LLM, keine Sitzungstabelle.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_screening_service.py
import pytest

from app.content.loader import load_course
from app.repositories import profile_repo
from app.screening import service
from tests.content_factory import MINIMAL_UNIT, write_course

PROBES = [
    {"id": "s1", "prompt_de": "Welcher Buchstabe klingt wie r?", "options": ["Р", "П"],
     "correct_index": 0, "maps_to_unit": 1},
    {"id": "s2", "prompt_de": "Was heißt я?", "options": ["ich", "du"],
     "correct_index": 0, "maps_to_unit": 2},
    {"id": "s3", "prompt_de": "Was heißt де́лаю?", "options": ["ich mache", "er macht"],
     "correct_index": 0, "maps_to_unit": 3},
]


@pytest.fixture
def course(tmp_path):
    units = [dict(MINIMAL_UNIT, id=index) for index in (1, 2, 3)]
    return load_course(write_course(tmp_path, units=units, screening=PROBES))


def test_first_probe_is_returned_without_the_answer(course):
    payload = service.probe_payload(course, 0)
    assert payload["prompt_de"].startswith("Welcher Buchstabe")
    assert payload["options"] == ["Р", "П"]
    assert payload["index"] == 0 and payload["total"] == 3
    assert "correct_index" not in payload


def test_next_step_serves_the_following_probe_after_a_correct_answer(course):
    step = service.next_step(course, [0])
    assert step["finished"] is False
    assert step["probe"]["index"] == 1


def test_next_step_continues_after_a_single_wrong_answer(course):
    step = service.next_step(course, [1])
    assert step["finished"] is False
    assert step["probe"]["index"] == 1


def test_two_consecutive_wrong_answers_end_the_screening(course):
    step = service.next_step(course, [1, 1])
    assert step["finished"] is True


def test_screening_ends_after_the_last_probe(course):
    step = service.next_step(course, [0, 0, 0])
    assert step["finished"] is True
    assert step["placement_unit"] == 3


def test_placement_uses_the_last_correct_probe(course):
    assert service.placement_unit_for(course, [0, 0, 1]) == 2


def test_placement_is_at_least_unit_one(course):
    assert service.placement_unit_for(course, [1, 1]) == 1


def test_finish_screening_persists_placement_and_result(conn, course):
    unit = service.finish_screening(conn, course, [0, 0, 1])
    assert unit == 2
    assert profile_repo.get_or_create_profile(conn, "russian").placement_unit == 2
    row = conn.execute("SELECT * FROM screening_results").fetchone()
    assert row["placement_unit"] == 2


def test_out_of_range_answer_counts_as_wrong(course):
    assert service.placement_unit_for(course, [99]) == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && .venv/bin/pytest tests/test_screening_service.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.screening'`

- [ ] **Step 3: Implement the screening service**

```python
# backend/app/screening/service.py
import datetime as dt
import json
from sqlite3 import Connection

from app.content.models import Course
from app.repositories.profile_repo import update_profile

WRONG_STREAK_TO_STOP = 2


def probe_payload(course: Course, index: int) -> dict:
    probe = course.screening[index]
    return {
        "id": probe.id,
        "index": index,
        "total": len(course.screening),
        "prompt_de": probe.prompt_de,
        "options": list(probe.options),
    }


def _is_correct(course: Course, index: int, answer: int) -> bool:
    return index < len(course.screening) and answer == course.screening[index].correct_index


def _should_stop(course: Course, answers: list[int]) -> bool:
    if len(answers) >= len(course.screening):
        return True
    streak = 0
    for index, answer in enumerate(answers):
        streak = 0 if _is_correct(course, index, answer) else streak + 1
        if streak >= WRONG_STREAK_TO_STOP:
            return True
    return False


def placement_unit_for(course: Course, answers: list[int]) -> int:
    """The unit to start at: after the last probe the learner got right."""
    unit = 1
    for index, answer in enumerate(answers):
        if _is_correct(course, index, answer):
            unit = max(unit, course.screening[index].maps_to_unit)
    return unit


def next_step(course: Course, answers: list[int]) -> dict:
    if _should_stop(course, answers):
        return {"finished": True, "placement_unit": placement_unit_for(course, answers)}
    return {"finished": False, "probe": probe_payload(course, len(answers))}


def finish_screening(conn: Connection, course: Course, answers: list[int]) -> int:
    unit = placement_unit_for(course, answers)
    conn.execute(
        "INSERT INTO screening_results (answers_json, placement_unit, created_at) VALUES (?, ?, ?)",
        (json.dumps(answers), unit, dt.datetime.now(dt.timezone.utc).isoformat()),
    )
    conn.commit()
    update_profile(conn, placement_unit=unit)
    return unit
```

Create `backend/app/screening/__init__.py` as an empty file.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && .venv/bin/pytest tests/test_screening_service.py -v`
Expected: PASS (9 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/screening backend/tests/test_screening_service.py
git commit -m "feat: add adaptive click-based placement screening"
```

---

## Task 8: Konfiguration und API-Endpunkte

**Files:**
- Modify: `backend/app/config.py`
- Modify: `backend/app/dependencies.py`
- Modify: `backend/app/api/schemas.py`
- Modify: `backend/app/api/routes.py`
- Modify: `docker-compose.yml`
- Test: `backend/tests/test_course_routes.py`

**Interfaces:**
- Consumes: `course_overview`, `unit_payload`, `submit_answer` aus `app.course.service`; `build_review_round`, `grade_review_round` aus `app.course.review`; `next_step`, `probe_payload`, `finish_screening` aus `app.screening.service`; `get_or_create_profile`, `update_profile` aus `app.repositories.profile_repo`
- Produces: `get_course() -> Course` aus `app.dependencies`; die Endpunkte aus Spec §7

- [ ] **Step 1: Write the failing route test**

```python
# backend/tests/test_course_routes.py
import pytest
from fastapi.testclient import TestClient

from app.content.loader import load_course
from app.course.presenter import build_sentence_tiles
from app.db import get_connection
from app.dependencies import get_course, get_db
from app.main import app
from tests.content_factory import write_course


@pytest.fixture
def course(tmp_path):
    return load_course(write_course(tmp_path / "content"))


@pytest.fixture
def client(db_path, course):
    def override_db():
        conn = get_connection(db_path)
        try:
            yield conn
        finally:
            conn.close()

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_course] = lambda: course
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_course_endpoint_lists_stages(client):
    response = client.get("/api/course")
    assert response.status_code == 200
    assert response.json()["stages"][0]["units"][0]["id"] == 1


def test_unit_endpoint_returns_exercises_without_solutions(client):
    body = client.get("/api/units/1").json()
    assert body["grammar_focus"]["title_de"]
    assert len(body["exercises"]) == 4
    assert "solution" not in body["exercises"][0]


def test_unit_endpoint_404s_for_unknown_unit(client):
    assert client.get("/api/units/999").status_code == 404


def test_answer_endpoint_grades_and_reports_progress(client, course):
    exercise = course.units[1].exercises[0]
    tiles = build_sentence_tiles(course, exercise)
    body = client.post(
        "/api/units/1/answer",
        json={
            "exercise_id": exercise.id,
            "submission": {"tile_indices": [tiles.index(ref) for ref in exercise.solution]},
        },
    ).json()
    assert body["correct"] is True
    assert body["solution_text"] == "я де́лаю"
    assert body["unit_completed"] is False


def test_answer_endpoint_404s_for_unknown_exercise(client):
    response = client.post(
        "/api/units/1/answer", json={"exercise_id": "nope", "submission": {}}
    )
    assert response.status_code == 404


def test_screening_start_returns_first_probe(client):
    body = client.post("/api/screening/start").json()
    assert body["finished"] is False
    assert body["probe"]["index"] == 0


def test_screening_answer_finishes_and_persists_placement(client):
    body = client.post("/api/screening/answer", json={"answers": [0]}).json()
    assert body["finished"] is True
    assert body["placement_unit"] == 1
    assert client.get("/api/profile").json()["placement_unit"] == 1


def test_review_due_is_empty_initially(client):
    assert client.get("/api/review/due").json()["left"] == []


def test_profile_patch_toggles_transliteration(client):
    body = client.patch("/api/profile", json={"show_transliteration": False}).json()
    assert body["show_transliteration"] is False


def test_explain_falls_back_to_the_unit_rule_when_ollama_fails(client, monkeypatch):
    from app.api import routes

    class Boom:
        def chat(self, messages):
            raise RuntimeError("ollama down")

    app.dependency_overrides[routes.get_ollama] = lambda: Boom()
    body = client.post(
        "/api/explain", json={"unit_id": 1, "exercise_id": "1-1", "chosen_text": "де́лает я"}
    ).json()
    assert body["source"] == "rule"
    assert body["explanation_de"] == "Die Endung zeigt, wer handelt."
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && .venv/bin/pytest tests/test_course_routes.py -v`
Expected: FAIL — `ImportError: cannot import name 'get_course' from 'app.dependencies'`

- [ ] **Step 3: Extend the configuration**

```python
# backend/app/config.py
import os
from dataclasses import dataclass
from pathlib import Path

DEFAULT_CONTENT_DIR = str(Path(__file__).resolve().parents[2] / "content" / "ru")


@dataclass(frozen=True)
class Settings:
    ollama_host: str = os.environ.get("OLLAMA_HOST", "http://ollama:11434")
    ollama_model: str = os.environ.get("OLLAMA_MODEL", "llama3.2:3b")
    db_path: str = os.environ.get("DB_PATH", "./data/speaker.db")
    default_language: str = os.environ.get("DEFAULT_LANGUAGE", "russian")
    content_dir: str = os.environ.get("CONTENT_DIR", DEFAULT_CONTENT_DIR)


settings = Settings()
```

- [ ] **Step 4: Add the course dependency**

```python
# append to backend/app/dependencies.py
from functools import lru_cache

from app.content.loader import load_course
from app.content.models import Course


@lru_cache(maxsize=1)
def _load_course() -> Course:
    return load_course(settings.content_dir, language=settings.default_language)


def get_course() -> Course:
    """The content package, loaded once per process."""
    return _load_course()
```

- [ ] **Step 5: Add the response schemas**

```python
# append to backend/app/api/schemas.py
class ProfileResponse(BaseModel):
    language: str
    cefr_level: str
    show_transliteration: bool = True
    placement_unit: int | None = None


class ProfilePatchRequest(BaseModel):
    show_transliteration: bool | None = None
    placement_unit: int | None = None


class AnswerRequest(BaseModel):
    exercise_id: str
    submission: dict


class AnswerResponse(BaseModel):
    correct: bool
    solution_text: str
    solution_translit: str
    explanation_de: str
    unit_completed: bool
    correct_count: int
    total_count: int


class ScreeningAnswerRequest(BaseModel):
    answers: list[int]


class ReviewAnswerRequest(BaseModel):
    pairs: list[list[int]]


class ExplainRequest(BaseModel):
    unit_id: int
    exercise_id: str
    chosen_text: str


class ExplainResponse(BaseModel):
    explanation_de: str
    source: str
```

Delete the old `ProfileResponse` definition so only the extended one remains.

- [ ] **Step 6: Add the routes**

```python
# append to backend/app/api/routes.py
from fastapi import HTTPException

from app.api.schemas import (
    AnswerRequest,
    AnswerResponse,
    ExplainRequest,
    ExplainResponse,
    ProfilePatchRequest,
    ReviewAnswerRequest,
    ScreeningAnswerRequest,
)
from app.content.models import Course
from app.course import review as review_module
from app.course import service as course_service
from app.dependencies import get_course
from app.screening import service as screening_service


@router.get("/course")
def read_course(
    conn: Connection = Depends(get_db), course: Course = Depends(get_course)
) -> dict:
    return course_service.course_overview(course, conn)


@router.get("/units/{unit_id}")
def read_unit(
    unit_id: int, conn: Connection = Depends(get_db), course: Course = Depends(get_course)
) -> dict:
    if unit_id not in course.units:
        raise HTTPException(status_code=404, detail=f"Einheit {unit_id} gibt es nicht")
    return course_service.unit_payload(course, conn, unit_id)


@router.post("/units/{unit_id}/answer", response_model=AnswerResponse)
def answer_unit(
    unit_id: int,
    payload: AnswerRequest,
    conn: Connection = Depends(get_db),
    course: Course = Depends(get_course),
) -> AnswerResponse:
    if unit_id not in course.units:
        raise HTTPException(status_code=404, detail=f"Einheit {unit_id} gibt es nicht")
    try:
        outcome = course_service.submit_answer(
            conn,
            course,
            unit_id=unit_id,
            exercise_id=payload.exercise_id,
            submission=payload.submission,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return AnswerResponse(**vars(outcome))


@router.post("/screening/start")
def screening_start(course: Course = Depends(get_course)) -> dict:
    return screening_service.next_step(course, [])


@router.post("/screening/answer")
def screening_answer(
    payload: ScreeningAnswerRequest,
    conn: Connection = Depends(get_db),
    course: Course = Depends(get_course),
) -> dict:
    step = screening_service.next_step(course, payload.answers)
    if step["finished"]:
        screening_service.finish_screening(conn, course, payload.answers)
    return step


@router.get("/review/due")
def review_due(
    conn: Connection = Depends(get_db), course: Course = Depends(get_course)
) -> dict:
    return review_module.build_review_round(conn, course, today=dt.date.today().isoformat())


@router.post("/review/answer")
def review_answer(
    payload: ReviewAnswerRequest,
    conn: Connection = Depends(get_db),
    course: Course = Depends(get_course),
) -> dict:
    return review_module.grade_review_round(
        conn,
        course,
        today=dt.date.today().isoformat(),
        submission={"pairs": payload.pairs},
    )


@router.patch("/profile", response_model=ProfileResponse)
def patch_profile(
    payload: ProfilePatchRequest, conn: Connection = Depends(get_db)
) -> ProfileResponse:
    profile = update_profile(
        conn,
        show_transliteration=payload.show_transliteration,
        placement_unit=payload.placement_unit,
    )
    return ProfileResponse(**vars(profile))


@router.post("/explain", response_model=ExplainResponse)
def explain(
    payload: ExplainRequest,
    course: Course = Depends(get_course),
    ollama: OllamaClient = Depends(get_ollama),
) -> ExplainResponse:
    unit = course.units.get(payload.unit_id)
    if unit is None:
        raise HTTPException(status_code=404, detail=f"Einheit {payload.unit_id} gibt es nicht")
    rule = unit.grammar_focus.explanation_de
    prompt = (
        "Du bist ein geduldiger Russischlehrer und antwortest auf Deutsch. "
        f"Die Regel dieser Lektion lautet: {rule} "
        f"Der Lernende hat geantwortet: {payload.chosen_text!r}. "
        "Erkläre in höchstens zwei Sätzen, warum das nicht passt. "
        "Erfinde keine neuen russischen Wörter."
    )
    try:
        text = ollama.chat([{"role": "user", "content": prompt}]).strip()
    except Exception:
        return ExplainResponse(explanation_de=rule, source="rule")
    return ExplainResponse(explanation_de=text or rule, source="llm" if text else "rule")
```

Add `import datetime as dt` at the top of `routes.py`, extend the existing `read_profile` handler to return the new fields via `ProfileResponse(**vars(profile))`, and make sure `get_ollama` and `update_profile` are imported there.

- [ ] **Step 7: Point docker-compose at Russian**

In `docker-compose.yml`, change the backend environment entry `DEFAULT_LANGUAGE=english` to `DEFAULT_LANGUAGE=russian` and add `- CONTENT_DIR=/app/content/ru`. In `backend/Dockerfile`, copy the content package into the image by adding `COPY ../content /app/content` — if the build context forbids that, change the compose build context to the repository root with `context: .` and `dockerfile: backend/Dockerfile`, and adjust the existing `COPY` paths accordingly.

- [ ] **Step 8: Run the full backend suite**

Run: `cd backend && .venv/bin/pytest -v`
Expected: PASS — inklusive der bestehenden `test_routes.py`

- [ ] **Step 9: Commit**

```bash
git add backend/app docker-compose.yml backend/tests/test_course_routes.py
git commit -m "feat: expose course, screening, review and explain endpoints"
```

---
## Task 9: Seed-Content — Lexikon, Einheiten 1–6, Screening

**Files:**
- Create: `content/ru/lexicon.json`
- Create: `content/ru/screening.json`
- Create: `content/ru/units/001.json` … `006.json`
- Test: `backend/tests/test_real_content.py`

**Interfaces:**
- Consumes: `load_course`, `validate_course`
- Produces: das reale Content-Paket unter `content/ru/`

Einheiten 1–4 bilden Stufe 0 (Schrift), Einheiten 5–6 den Anfang von Stufe 1. Alle weiteren Einheiten entstehen im Folgeplan. Jede Einheit braucht mindestens 6 Aufgaben.

- [ ] **Step 1: Write the failing content test**

```python
# backend/tests/test_real_content.py
from pathlib import Path

from app.content.loader import load_course
from app.content.validator import validate_course

CONTENT_DIR = Path(__file__).resolve().parents[2] / "content" / "ru"


def test_shipped_content_passes_every_validation_rule():
    course = load_course(CONTENT_DIR)
    assert validate_course(course) == []


def test_shipped_content_has_the_seed_units():
    course = load_course(CONTENT_DIR)
    assert sorted(course.units) == [1, 2, 3, 4, 5, 6]


def test_stage_zero_teaches_letters_only():
    course = load_course(CONTENT_DIR)
    for unit_id in (1, 2, 3, 4):
        for lexeme_id in course.units[unit_id].new_lexemes:
            assert course.lexemes[lexeme_id].pos == "letter"


def test_every_exercise_type_appears_in_the_seed_content():
    course = load_course(CONTENT_DIR)
    types = {exercise.type for unit in course.units.values() for exercise in unit.exercises}
    assert types == {"build_sentence", "choose_form", "match_pairs", "dialog_reply"}


def test_screening_probes_are_ordered_by_the_unit_they_unlock():
    course = load_course(CONTENT_DIR)
    units = [probe.maps_to_unit for probe in course.screening]
    assert units == sorted(units)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && .venv/bin/pytest tests/test_real_content.py -v`
Expected: FAIL — `ContentError: Datei fehlt: lexicon.json`

- [ ] **Step 3: Write the letter lexemes for stage 0**

Every entry has `"pos": "letter"` and a single `"base"` form whose `text` is the letter pair (upper and lower case) and whose `translit` is the Latin sound. Write all 32 into `content/ru/lexicon.json`:

| id | text | translit | gloss_de |
|---|---|---|---|
| `bu_r` | `Р р` | `r` | klingt wie ein gerolltes **r** — nicht wie p |
| `bu_n` | `Н н` | `n` | klingt wie **n** — nicht wie h |
| `bu_v` | `В в` | `v` | klingt wie **w** in Wasser |
| `bu_s` | `С с` | `s` | klingt wie stimmloses **s** in Bus |
| `bu_u` | `У у` | `u` | klingt wie **u** in Buch |
| `bu_h` | `Х х` | `ch` | klingt wie **ch** in Bach |
| `bu_zh` | `Ж ж` | `ž` | klingt wie **j** in Journal |
| `bu_ts` | `Ц ц` | `c` | klingt wie **z** in Zahn |
| `bu_ch` | `Ч ч` | `č` | klingt wie **tsch** in Tschüss |
| `bu_sh` | `Ш ш` | `š` | klingt wie **sch** in Schule |
| `bu_shch` | `Щ щ` | `šč` | klingt wie ein weiches, langes **schsch** |
| `bu_e` | `Э э` | `e` | klingt wie **ä** in Bär |
| `bu_yu` | `Ю ю` | `ju` | klingt wie **ju** in Jude |
| `bu_ya` | `Я я` | `ja` | klingt wie **ja** |
| `bu_b` | `Б б` | `b` | klingt wie **b** |
| `bu_g` | `Г г` | `g` | klingt wie **g** |
| `bu_d` | `Д д` | `d` | klingt wie **d** |
| `bu_z` | `З з` | `z` | klingt wie stimmhaftes **s** in Rose |
| `bu_i` | `И и` | `i` | klingt wie **i** in Liebe |
| `bu_j` | `Й й` | `j` | kurzes **i** am Silbenende, wie in Mai |
| `bu_l` | `Л л` | `l` | klingt wie **l** |
| `bu_p` | `П п` | `p` | klingt wie **p** |
| `bu_f` | `Ф ф` | `f` | klingt wie **f** |
| `bu_y` | `Ы ы` | `y` | dumpfes **i**, zwischen i und ü |
| `bu_a` | `А а` | `a` | klingt wie **a** |
| `bu_o` | `О о` | `o` | betont **o**, unbetont eher **a** |
| `bu_k` | `К к` | `k` | klingt wie **k** |
| `bu_m` | `М м` | `m` | klingt wie **m** |
| `bu_t` | `Т т` | `t` | klingt wie **t** |
| `bu_yo` | `Ё ё` | `jo` | klingt wie **jo** — trägt immer die Betonung |
| `bu_soft` | `ь` | `'` | weiches Zeichen — macht den Buchstaben davor weich |
| `bu_hard` | `ъ` | `''` | hartes Zeichen — trennt, wird nicht gesprochen |

- [ ] **Step 4: Write the word lexemes for units 5 and 6**

Append these entries to `content/ru/lexicon.json`:

```json
{"id": "privet", "lemma": "приве́т", "pos": "interj", "gloss_de": "hallo (locker)",
 "forms": {"base": {"text": "приве́т", "translit": "privét"}}},
{"id": "zdravstvujte", "lemma": "здра́вствуйте", "pos": "interj", "gloss_de": "guten Tag (förmlich)",
 "forms": {"base": {"text": "здра́вствуйте", "translit": "zdrávstvujte"}}},
{"id": "poka", "lemma": "пока́", "pos": "interj", "gloss_de": "tschüss (locker)",
 "forms": {"base": {"text": "пока́", "translit": "poká"}}},
{"id": "do", "lemma": "до", "pos": "prep", "gloss_de": "bis",
 "forms": {"base": {"text": "до", "translit": "do"}}},
{"id": "svidanie", "lemma": "свида́ние", "pos": "noun", "gloss_de": "das Wiedersehen",
 "forms": {"nom.sg": {"text": "свида́ние", "translit": "svidánije"},
           "gen.sg": {"text": "свида́ния", "translit": "svidánija"}}},
{"id": "spasibo", "lemma": "спаси́бо", "pos": "interj", "gloss_de": "danke",
 "forms": {"base": {"text": "спаси́бо", "translit": "spasíbo"}}},
{"id": "bolshoe", "lemma": "большо́е", "pos": "adj", "gloss_de": "groß",
 "forms": {"nom.n": {"text": "большо́е", "translit": "bol'šóje"}}},
{"id": "pozhalujsta", "lemma": "пожа́луйста", "pos": "part", "gloss_de": "bitte",
 "forms": {"base": {"text": "пожа́луйста", "translit": "požálujsta"}}},
{"id": "ja", "lemma": "я", "pos": "pron", "gloss_de": "ich",
 "forms": {"nom": {"text": "я", "translit": "ja"},
           "acc": {"text": "меня́", "translit": "menjá"}}},
{"id": "ty", "lemma": "ты", "pos": "pron", "gloss_de": "du",
 "forms": {"nom": {"text": "ты", "translit": "ty"},
           "acc": {"text": "тебя́", "translit": "tebjá"},
           "dat": {"text": "тебе́", "translit": "tebé"}}},
{"id": "vy", "lemma": "вы", "pos": "pron", "gloss_de": "Sie (förmlich), ihr",
 "forms": {"nom": {"text": "вы", "translit": "vy"},
           "acc": {"text": "вас", "translit": "vas"},
           "dat": {"text": "вам", "translit": "vam"}}},
{"id": "kak", "lemma": "как", "pos": "adv", "gloss_de": "wie",
 "forms": {"base": {"text": "как", "translit": "kak"}}},
{"id": "zvat", "lemma": "звать", "pos": "verb", "gloss_de": "nennen, rufen", "aspect": "impf",
 "forms": {"inf": {"text": "звать", "translit": "zvat'"},
           "prs.3pl": {"text": "зову́т", "translit": "zovút"}}},
{"id": "ochen", "lemma": "о́чень", "pos": "adv", "gloss_de": "sehr",
 "forms": {"base": {"text": "о́чень", "translit": "óčen'"}}},
{"id": "prijatno", "lemma": "прия́тно", "pos": "adv", "gloss_de": "angenehm",
 "forms": {"base": {"text": "прия́тно", "translit": "prijátno"}}}
```

- [ ] **Step 5: Write the four stage-0 units**

Each unit gets `"stage": 0`, six `match_pairs` exercises, and its letters listed in `new_lexemes`. Distribute the letters like this:

| Unit | `title_de` | `grammar_focus.title_de` | Letters |
|---|---|---|---|
| 001 | Buchstaben, die täuschen | Vertraute Formen, neuer Klang | `bu_r bu_n bu_v bu_s bu_u bu_h` |
| 002 | Neue Zeichen | Laute, die es im Deutschen nicht einzeln gibt | `bu_zh bu_ts bu_ch bu_sh bu_shch bu_e bu_yu bu_ya` |
| 003 | Die einfachen Buchstaben | Zeichen, die klingen wie sie aussehen | `bu_b bu_g bu_d bu_z bu_i bu_j bu_l bu_p bu_f bu_y` |
| 004 | Weich, hart und betont | Zeichen ohne eigenen Laut, und warum Betonung zählt | `bu_a bu_o bu_k bu_m bu_t bu_yo bu_soft bu_hard` |

`explanation_de` für Einheit 001 (die anderen analog, je 3–4 Sätze):

> Sechs russische Buchstaben sehen aus wie lateinische, klingen aber ganz anders. Р ist kein p, sondern ein gerolltes r. Н ist kein h, sondern ein n, und В klingt wie ein deutsches w. Wenn du diese sechs sicher hast, kannst du die meisten Wörter schon halbwegs lesen.

Die sechs Aufgaben je Einheit sind `match_pairs` über je 3–4 Buchstaben, sodass jeder Buchstabe der Einheit in mindestens zwei Aufgaben vorkommt. Beispiel für Einheit 001, Aufgabe 1:

```json
{"id": "1-1", "type": "match_pairs", "prompt_de": "Ordne jedem Buchstaben seinen Klang zu.",
 "pairs": [["bu_r", "base"], ["bu_n", "base"], ["bu_v", "base"]]}
```

- [ ] **Step 6: Write unit 005 — Begrüßen und verabschieden**

```json
{
  "id": 5, "stage": 1,
  "title_de": "Hallo und tschüss",
  "scenario_de": "Du triffst jemanden auf der Straße und verabschiedest dich wieder.",
  "grammar_focus": {
    "id": "formal-informal",
    "title_de": "Locker oder förmlich?",
    "explanation_de": "Russisch unterscheidet klar zwischen locker und förmlich. Zu Freunden sagst du приве́т und пока́. Zu Fremden, im Laden oder im Amt sagst du здра́вствуйте und до свида́ния. Wer im Zweifel die förmliche Form nimmt, macht nie etwas falsch.",
  },
  "new_lexemes": ["privet", "zdravstvujte", "poka", "do", "svidanie", "spasibo", "bolshoe", "pozhalujsta"],
  "exercises": [
    {"id": "5-1", "type": "match_pairs", "prompt_de": "Ordne die Begrüßungen zu.",
     "pairs": [["privet", "base"], ["zdravstvujte", "base"], ["poka", "base"]]},
    {"id": "5-2", "type": "match_pairs", "prompt_de": "Ordne zu.",
     "pairs": [["spasibo", "base"], ["pozhalujsta", "base"], ["svidanie", "nom.sg"]]},
    {"id": "5-3", "type": "build_sentence", "prompt_de": "Auf Wiedersehen!",
     "solution": [["do", "base"], ["svidanie", "gen.sg"]],
     "distractors": [["svidanie", "nom.sg"], ["poka", "base"]]},
    {"id": "5-4", "type": "build_sentence", "prompt_de": "Vielen Dank!",
     "solution": [["spasibo", "base"], ["bolshoe", "nom.n"]],
     "distractors": [["pozhalujsta", "base"]]},
    {"id": "5-5", "type": "choose_form", "prompt_de": "Auf Wiedersehen! — Welche Form steht nach до?",
     "sentence": [["do", "base"], "___"],
     "answer": ["svidanie", "gen.sg"], "distractor_forms": ["nom.sg"]},
    {"id": "5-6", "type": "dialog_reply", "prompt_de": "Eine ältere Nachbarin grüßt dich. Was antwortest du?",
     "tutor_line": [["zdravstvujte", "base"]], "correct_index": 0,
     "options": [
       {"tokens": [["zdravstvujte", "base"]], "why_de": ""},
       {"tokens": [["poka", "base"]], "why_de": "пока́ heißt tschüss — das passt nicht als Begrüßung."},
       {"tokens": [["spasibo", "base"]], "why_de": "спаси́бо heißt danke, hier wird aber gegrüßt."}
     ]},
    {"id": "5-7", "type": "dialog_reply", "prompt_de": "Ein Freund sagt beim Gehen пока́. Was sagst du?",
     "tutor_line": [["poka", "base"]], "correct_index": 0,
     "options": [
       {"tokens": [["poka", "base"]], "why_de": ""},
       {"tokens": [["privet", "base"]], "why_de": "приве́т ist die Begrüßung, nicht der Abschied."}
     ]}
  ]
}
```

Note: das Komma nach `explanation_de` im Beispiel oben entfernen — JSON erlaubt kein nachgestelltes Komma.

- [ ] **Step 7: Write unit 006 — Wie heißt du?**

```json
{
  "id": 6, "stage": 1,
  "title_de": "Wie heißt du?",
  "scenario_de": "Du lernst jemanden kennen und fragst nach dem Namen.",
  "grammar_focus": {
    "id": "acc-pronouns",
    "title_de": "Wörtlich: „wie nennen sie dich?“",
    "explanation_de": "Russisch fragt nach dem Namen anders als Deutsch: Как тебя́ зову́т? heißt wörtlich „wie nennen sie dich?“. Das Pronomen steht deshalb im Akkusativ — меня́ (mich), тебя́ (dich), вас (Sie). Ein Wort für „ist“ oder „heiße“ gibt es hier nicht."
  },
  "new_lexemes": ["ja", "ty", "vy", "kak", "zvat", "ochen", "prijatno"],
  "exercises": [
    {"id": "6-1", "type": "match_pairs", "prompt_de": "Ordne die Pronomen zu.",
     "pairs": [["ja", "nom"], ["ty", "nom"], ["vy", "nom"]]},
    {"id": "6-2", "type": "build_sentence", "prompt_de": "Wie heißen Sie?",
     "solution": [["kak", "base"], ["vy", "acc"], ["zvat", "prs.3pl"]],
     "distractors": [["vy", "nom"], ["ty", "acc"]]},
    {"id": "6-3", "type": "build_sentence", "prompt_de": "Wie heißt du?",
     "solution": [["kak", "base"], ["ty", "acc"], ["zvat", "prs.3pl"]],
     "distractors": [["ty", "nom"], ["vy", "acc"]]},
    {"id": "6-4", "type": "choose_form", "prompt_de": "Wie heißt du? — Welche Form von ты passt?",
     "sentence": [["kak", "base"], "___", ["zvat", "prs.3pl"]],
     "answer": ["ty", "acc"], "distractor_forms": ["nom", "dat"]},
    {"id": "6-5", "type": "choose_form", "prompt_de": "Wie heißen Sie? — Welche Form von вы passt?",
     "sentence": [["kak", "base"], "___", ["zvat", "prs.3pl"]],
     "answer": ["vy", "acc"], "distractor_forms": ["nom", "dat"]},
    {"id": "6-6", "type": "build_sentence", "prompt_de": "Sehr angenehm!",
     "solution": [["ochen", "base"], ["prijatno", "base"]],
     "distractors": [["spasibo", "base"]]},
    {"id": "6-7", "type": "dialog_reply", "prompt_de": "Jemand fragt Как вас зову́т? Womit antwortest du sinnvoll?",
     "tutor_line": [["kak", "base"], ["vy", "acc"], ["zvat", "prs.3pl"]], "correct_index": 0,
     "options": [
       {"tokens": [["ochen", "base"], ["prijatno", "base"]], "why_de": ""},
       {"tokens": [["do", "base"], ["svidanie", "gen.sg"]], "why_de": "Das ist ein Abschied — das Gespräch fängt gerade erst an."}
     ]}
  ]
}
```

- [ ] **Step 8: Write the screening probes**

`content/ru/screening.json` mit `{"probes": [...]}`, aufsteigend sortiert nach `maps_to_unit`. Sechs Sonden, jede mit drei Optionen und deutschsprachiger Frage:

`maps_to_unit` ist die Einheit, bei der der Lernende **einsteigt**, wenn dies seine letzte richtige
Sonde war — also stets die Einheit *nach* dem geprüften Stoff.

| id | prompt_de | options | correct_index | prüft | maps_to_unit |
|---|---|---|---|---|---|
| `s1` | Welcher Buchstabe klingt wie ein gerolltes r? | `Р`, `П`, `Г` | 0 | Einheit 1 | 2 |
| `s2` | Wie klingt Ж? | `wie j in Journal`, `wie ch in Bach`, `wie z in Zahn` | 0 | Einheit 2 | 3 |
| `s3` | Welches Zeichen wird gar nicht gesprochen? | `ъ`, `ы`, `ю` | 0 | Einheit 3–4 | 5 |
| `s4` | Welches Wort heißt „danke“? | `спаси́бо`, `пожа́луйста`, `пока́` | 0 | Einheit 5 | 6 |
| `s5` | Was heißt до свида́ния? | `auf Wiedersehen`, `guten Tag`, `bitte sehr` | 0 | Einheit 5 | 6 |
| `s6` | Welche Form passt: Как ___ зову́т? (Wie heißt du?) | `тебя́`, `ты`, `тебе́` | 0 | Einheit 6 | 6 |

Wer alles richtig hat, startet bei Einheit 6 — mehr Inhalt gibt es nach diesem Plan noch nicht.
Mit den Einheiten aus dem Folgeplan kommen weitere Sonden dazu.

- [ ] **Step 9: Validate and run the tests**

Run: `cd backend && .venv/bin/python -m scripts.validate_content`
Expected: `OK — 6 Einheiten, 47 Lexeme, 6 Sonden`

Run: `cd backend && .venv/bin/pytest tests/test_real_content.py -v`
Expected: PASS (5 tests)

Sollte der Validator meckern, ist der Content falsch — nicht der Validator. Korrigiere die JSON-Dateien, bis der Lauf sauber ist.

- [ ] **Step 10: Run the full backend suite**

Run: `cd backend && .venv/bin/pytest -v`
Expected: PASS

- [ ] **Step 11: Commit**

```bash
git add content backend/tests/test_real_content.py
git commit -m "content: add alphabet units and first two conversation units"
```

---
## Task 10: Frontend-Grundgerüst — Tailwind, Router, API-Schicht

**Files:**
- Modify: `frontend/package.json`, `frontend/vite.config.ts`, `frontend/src/main.tsx`, `frontend/src/App.tsx`, `frontend/index.html`
- Create: `frontend/src/index.css`
- Create: `frontend/src/courseTypes.ts`
- Create: `frontend/src/courseApi.ts`
- Modify: `frontend/src/App.test.tsx`

**Interfaces:**
- Consumes: die Endpunkte aus Task 8
- Produces: alle Typen aus `courseTypes.ts` und die Funktionen `getCourse`, `getUnit`, `submitAnswer`, `startScreening`, `answerScreening`, `getReviewRound`, `submitReviewRound`, `getProfile`, `patchProfile` aus `courseApi.ts`

- [ ] **Step 1: Install the new dependencies**

```bash
cd frontend && npm install react-router-dom@^6.26.2 && npm install -D tailwindcss@^4.0.0 @tailwindcss/vite@^4.0.0
```

- [ ] **Step 2: Wire Tailwind into Vite**

```ts
// frontend/vite.config.ts
/// <reference types="vitest" />
import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  test: {
    environment: "jsdom",
    setupFiles: "./src/setupTests.ts",
  },
});
```

```css
/* frontend/src/index.css */
@import "tailwindcss";
```

- [ ] **Step 3: Define the shared types**

```ts
// frontend/src/courseTypes.ts
export interface Word {
  text: string;
  translit: string;
}

export interface Tile extends Word {
  index: number;
}

export interface GlossOption {
  index: number;
  gloss_de: string;
}

export interface BuildSentenceExercise {
  id: string;
  type: "build_sentence";
  prompt_de: string;
  tiles: Tile[];
}

export interface ChooseFormExercise {
  id: string;
  type: "choose_form";
  prompt_de: string;
  sentence: (Word | null)[];
  options: Tile[];
}

export interface MatchPairsExercise {
  id: string;
  type: "match_pairs";
  prompt_de: string;
  left: Tile[];
  right: GlossOption[];
}

export interface DialogReplyExercise {
  id: string;
  type: "dialog_reply";
  prompt_de: string;
  tutor_line: Word[];
  options: Tile[];
}

export type Exercise =
  | BuildSentenceExercise
  | ChooseFormExercise
  | MatchPairsExercise
  | DialogReplyExercise;

export type Submission =
  | { tile_indices: number[] }
  | { option_index: number }
  | { pairs: number[][] };

export interface UnitDetail {
  id: number;
  stage: number;
  title_de: string;
  scenario_de: string;
  grammar_focus: { id: string; title_de: string; explanation_de: string };
  solved_exercise_ids: string[];
  exercises: Exercise[];
}

export interface UnitSummary {
  id: number;
  title_de: string;
  scenario_de: string;
  status: "not_started" | "in_progress" | "completed";
  correct_count: number;
  exercise_count: number;
}

export interface CourseOverview {
  stages: { stage: number; units: UnitSummary[] }[];
}

export interface AnswerResult {
  correct: boolean;
  solution_text: string;
  solution_translit: string;
  explanation_de: string;
  unit_completed: boolean;
  correct_count: number;
  total_count: number;
}

export interface ScreeningProbe {
  id: string;
  index: number;
  total: number;
  prompt_de: string;
  options: string[];
}

export type ScreeningStep =
  | { finished: false; probe: ScreeningProbe }
  | { finished: true; placement_unit: number };

export interface ReviewRound {
  left: (Tile & { ref: string })[];
  right: GlossOption[];
}

export interface ReviewResult {
  correct_count: number;
  total_count: number;
  results: { ref: string; correct: boolean; gloss_de: string; text: string }[];
}

export interface Profile {
  language: string;
  cefr_level: string;
  show_transliteration: boolean;
  placement_unit: number | null;
}
```

- [ ] **Step 4: Write the API client**

```ts
// frontend/src/courseApi.ts
import { API_BASE_URL } from "./api";
import type {
  AnswerResult,
  CourseOverview,
  Profile,
  ReviewResult,
  ReviewRound,
  ScreeningStep,
  Submission,
  UnitDetail,
} from "./courseTypes";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}/api${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!response.ok) {
    throw new Error(`Anfrage fehlgeschlagen (${response.status}): ${path}`);
  }
  return response.json() as Promise<T>;
}

export const getCourse = () => request<CourseOverview>("/course");

export const getUnit = (unitId: number) => request<UnitDetail>(`/units/${unitId}`);

export const submitAnswer = (unitId: number, exerciseId: string, submission: Submission) =>
  request<AnswerResult>(`/units/${unitId}/answer`, {
    method: "POST",
    body: JSON.stringify({ exercise_id: exerciseId, submission }),
  });

export const startScreening = () =>
  request<ScreeningStep>("/screening/start", { method: "POST" });

export const answerScreening = (answers: number[]) =>
  request<ScreeningStep>("/screening/answer", {
    method: "POST",
    body: JSON.stringify({ answers }),
  });

export const getReviewRound = () => request<ReviewRound>("/review/due");

export const submitReviewRound = (pairs: number[][]) =>
  request<ReviewResult>("/review/answer", {
    method: "POST",
    body: JSON.stringify({ pairs }),
  });

export const getProfile = () => request<Profile>("/profile");

export const patchProfile = (patch: Partial<Pick<Profile, "show_transliteration">>) =>
  request<Profile>("/profile", { method: "PATCH", body: JSON.stringify(patch) });
```

- [ ] **Step 5: Write the failing shell test**

```tsx
// frontend/src/App.test.tsx
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import App from "./App";

describe("App", () => {
  it("zeigt die Hauptnavigation", () => {
    render(
      <MemoryRouter initialEntries={["/kurs"]}>
        <App />
      </MemoryRouter>,
    );
    expect(screen.getByRole("link", { name: "Kurs" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Wiederholen" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Profil" })).toBeInTheDocument();
  });
});
```

- [ ] **Step 6: Run test to verify it fails**

Run: `cd frontend && npm test -- App`
Expected: FAIL — `Cannot find module 'react-router-dom'` oder fehlende Links

- [ ] **Step 7: Rebuild the app shell**

```tsx
// frontend/src/App.tsx
import { NavLink, Route, Routes } from "react-router-dom";

import ChatView from "./ChatView";
import CourseView from "./views/CourseView";
import ProfileView from "./ProfileView";
import ReviewView from "./views/ReviewView";
import ScreeningView from "./views/ScreeningView";
import UnitView from "./views/UnitView";

const TABS = [
  { to: "/kurs", label: "Kurs" },
  { to: "/wiederholen", label: "Wiederholen" },
  { to: "/profil", label: "Profil" },
];

export default function App() {
  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-3xl items-center gap-6 px-4 py-3">
          <span className="text-lg font-semibold">Speaker</span>
          <nav className="flex gap-4">
            {TABS.map((tab) => (
              <NavLink
                key={tab.to}
                to={tab.to}
                className={({ isActive }) =>
                  isActive ? "font-medium text-sky-700" : "text-slate-600 hover:text-slate-900"
                }
              >
                {tab.label}
              </NavLink>
            ))}
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-3xl px-4 py-6">
        <Routes>
          <Route path="/" element={<CourseView />} />
          <Route path="/kurs" element={<CourseView />} />
          <Route path="/kurs/:unitId" element={<UnitView />} />
          <Route path="/einstufung" element={<ScreeningView />} />
          <Route path="/wiederholen" element={<ReviewView />} />
          <Route path="/profil" element={<ProfileView />} />
          <Route path="/gespraech" element={<ChatView />} />
        </Routes>
      </main>
    </div>
  );
}
```

```tsx
// frontend/src/main.tsx
import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";

import App from "./App";
import "./index.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>,
);
```

Set the document language in `frontend/index.html` to `<html lang="de">`.

The four view modules do not exist yet — create them for now as one-line placeholders that render their German heading (`export default function CourseView() { return <h2>Kurs</h2>; }` and so on) so the shell compiles. Tasks 11–14 replace each of them with the real implementation.

- [ ] **Step 8: Run test to verify it passes**

Run: `cd frontend && npm test`
Expected: PASS — inklusive der bestehenden Tests. Bestehende Tests, die `App` ohne Router rendern, in einen `MemoryRouter` einwickeln.

- [ ] **Step 9: Commit**

```bash
git add frontend
git commit -m "feat: add routing, tailwind and course api client to frontend"
```

---
## Task 11: Russische Textdarstellung und Wortkachel

**Files:**
- Create: `frontend/src/course/TransliterationContext.tsx`
- Create: `frontend/src/course/RussianText.tsx`
- Create: `frontend/src/course/Tile.tsx`
- Modify: `frontend/src/App.tsx` (Provider einhängen)
- Test: `frontend/src/course/RussianText.test.tsx`
- Test: `frontend/src/course/Tile.test.tsx`

**Interfaces:**
- Consumes: `Word` aus `courseTypes`, `getProfile`/`patchProfile` aus `courseApi`
- Produces:
  - `TransliterationProvider`, `useTransliteration(): { show: boolean; setShow(value: boolean): void }` aus `course/TransliterationContext`
  - `RussianText({ word, className })` aus `course/RussianText`
  - `Tile({ word, state, onClick, disabled })` mit `state: "idle" | "selected" | "correct" | "wrong"` aus `course/Tile`

- [ ] **Step 1: Write the failing tests**

```tsx
// frontend/src/course/RussianText.test.tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import RussianText from "./RussianText";
import { TransliterationContext } from "./TransliterationContext";

const word = { text: "приве́т", translit: "privét" };

function renderWith(show: boolean) {
  return render(
    <TransliterationContext.Provider value={{ show, setShow: () => {} }}>
      <RussianText word={word} />
    </TransliterationContext.Provider>,
  );
}

describe("RussianText", () => {
  it("zeigt immer den kyrillischen Text", () => {
    renderWith(false);
    expect(screen.getByText("приве́т")).toBeInTheDocument();
  });

  it("zeigt die Umschrift, wenn sie eingeschaltet ist", () => {
    renderWith(true);
    expect(screen.getByText("privét")).toBeInTheDocument();
  });

  it("blendet die Umschrift aus, wenn sie abgeschaltet ist", () => {
    renderWith(false);
    expect(screen.queryByText("privét")).not.toBeInTheDocument();
  });
});
```

```tsx
// frontend/src/course/Tile.test.tsx
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import Tile from "./Tile";

const word = { text: "я", translit: "ja" };

describe("Tile", () => {
  it("meldet einen Klick", () => {
    const onClick = vi.fn();
    render(<Tile word={word} state="idle" onClick={onClick} />);
    fireEvent.click(screen.getByRole("button", { name: /я/ }));
    expect(onClick).toHaveBeenCalledOnce();
  });

  it("meldet keinen Klick, wenn sie deaktiviert ist", () => {
    const onClick = vi.fn();
    render(<Tile word={word} state="idle" onClick={onClick} disabled />);
    fireEvent.click(screen.getByRole("button", { name: /я/ }));
    expect(onClick).not.toHaveBeenCalled();
  });

  it("markiert den Zustand für Hilfstechnologien", () => {
    render(<Tile word={word} state="selected" onClick={() => {}} />);
    expect(screen.getByRole("button", { name: /я/ })).toHaveAttribute("aria-pressed", "true");
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && npm test -- course`
Expected: FAIL — Module `./RussianText` und `./Tile` fehlen

- [ ] **Step 3: Implement the transliteration context**

```tsx
// frontend/src/course/TransliterationContext.tsx
import { createContext, useContext, useEffect, useState } from "react";
import type { ReactNode } from "react";

import { getProfile, patchProfile } from "../courseApi";

interface TransliterationValue {
  show: boolean;
  setShow: (value: boolean) => void;
}

export const TransliterationContext = createContext<TransliterationValue>({
  show: true,
  setShow: () => {},
});

export function useTransliteration(): TransliterationValue {
  return useContext(TransliterationContext);
}

export function TransliterationProvider({ children }: { children: ReactNode }) {
  const [show, setShowState] = useState(true);

  useEffect(() => {
    getProfile()
      .then((profile) => setShowState(profile.show_transliteration))
      .catch(() => setShowState(true));
  }, []);

  const setShow = (value: boolean) => {
    setShowState(value);
    patchProfile({ show_transliteration: value }).catch(() => {});
  };

  return (
    <TransliterationContext.Provider value={{ show, setShow }}>
      {children}
    </TransliterationContext.Provider>
  );
}
```

- [ ] **Step 4: Implement RussianText and Tile**

```tsx
// frontend/src/course/RussianText.tsx
import type { Word } from "../courseTypes";
import { useTransliteration } from "./TransliterationContext";

export default function RussianText({ word, className = "" }: { word: Word; className?: string }) {
  const { show } = useTransliteration();
  return (
    <span className={`inline-flex flex-col items-center leading-tight ${className}`}>
      <span lang="ru">{word.text}</span>
      {show && word.translit ? (
        <span className="text-xs text-slate-500">{word.translit}</span>
      ) : null}
    </span>
  );
}
```

```tsx
// frontend/src/course/Tile.tsx
import type { Word } from "../courseTypes";
import RussianText from "./RussianText";

export type TileState = "idle" | "selected" | "correct" | "wrong";

const STYLES: Record<TileState, string> = {
  idle: "border-slate-300 bg-white hover:border-sky-400",
  selected: "border-sky-500 bg-sky-50",
  correct: "border-emerald-500 bg-emerald-50",
  wrong: "border-rose-500 bg-rose-50",
};

export default function Tile({
  word,
  state,
  onClick,
  disabled = false,
}: {
  word: Word;
  state: TileState;
  onClick: () => void;
  disabled?: boolean;
}) {
  return (
    <button
      type="button"
      aria-pressed={state === "selected"}
      disabled={disabled}
      onClick={onClick}
      className={`rounded-xl border-2 px-4 py-2 text-lg transition disabled:opacity-60 ${STYLES[state]}`}
    >
      <RussianText word={word} />
    </button>
  );
}
```

- [ ] **Step 5: Wrap the app in the provider**

In `frontend/src/App.tsx`, import `TransliterationProvider` and wrap the returned `<div>` in it.

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd frontend && npm test`
Expected: PASS (6 neue Tests)

- [ ] **Step 7: Commit**

```bash
git add frontend/src/course frontend/src/App.tsx
git commit -m "feat: add russian text rendering with toggleable transliteration"
```

---

## Task 12: Die vier Übungskomponenten

**Files:**
- Create: `frontend/src/course/BuildSentenceExercise.tsx`
- Create: `frontend/src/course/ChooseFormExercise.tsx`
- Create: `frontend/src/course/MatchPairsExercise.tsx`
- Create: `frontend/src/course/DialogReplyExercise.tsx`
- Create: `frontend/src/course/ExerciseRunner.tsx`
- Test: `frontend/src/course/exercises.test.tsx`

**Interfaces:**
- Consumes: `Tile`, `RussianText`, die Aufgaben-Typen aus `courseTypes`
- Produces: alle vier Komponenten mit der einheitlichen Signatur `({ exercise, disabled, onSubmit })`, wobei `onSubmit(submission: Submission)` aufgerufen wird; sowie `ExerciseRunner({ exercise, disabled, onSubmit })`, das anhand von `exercise.type` die passende Komponente wählt

Alle vier Komponenten sammeln nur die Auswahl und rufen `onSubmit` — die Bewertung passiert im Backend. Keine Komponente kennt die Lösung.

Vor der Umsetzung dieses Tasks: das Skill `frontend-design` laden und die dort beschriebene Gestaltungsrichtung auf die Kachel-Optik anwenden.

- [ ] **Step 1: Write the failing tests**

```tsx
// frontend/src/course/exercises.test.tsx
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import BuildSentenceExercise from "./BuildSentenceExercise";
import ChooseFormExercise from "./ChooseFormExercise";
import DialogReplyExercise from "./DialogReplyExercise";
import MatchPairsExercise from "./MatchPairsExercise";

const build = {
  id: "6-2",
  type: "build_sentence" as const,
  prompt_de: "Wie heißen Sie?",
  tiles: [
    { index: 0, text: "зову́т", translit: "zovút" },
    { index: 1, text: "как", translit: "kak" },
    { index: 2, text: "вас", translit: "vas" },
  ],
};

describe("BuildSentenceExercise", () => {
  it("baut den Satz in Klickreihenfolge", () => {
    const onSubmit = vi.fn();
    render(<BuildSentenceExercise exercise={build} onSubmit={onSubmit} />);
    fireEvent.click(screen.getByRole("button", { name: /как/ }));
    fireEvent.click(screen.getByRole("button", { name: /вас/ }));
    fireEvent.click(screen.getByRole("button", { name: /зову́т/ }));
    fireEvent.click(screen.getByRole("button", { name: "Prüfen" }));
    expect(onSubmit).toHaveBeenCalledWith({ tile_indices: [1, 2, 0] });
  });

  it("nimmt eine Kachel per erneutem Klick wieder heraus", () => {
    const onSubmit = vi.fn();
    render(<BuildSentenceExercise exercise={build} onSubmit={onSubmit} />);
    fireEvent.click(screen.getByRole("button", { name: /как/ }));
    fireEvent.click(screen.getByRole("button", { name: /как/ }));
    fireEvent.click(screen.getByRole("button", { name: /вас/ }));
    fireEvent.click(screen.getByRole("button", { name: "Prüfen" }));
    expect(onSubmit).toHaveBeenCalledWith({ tile_indices: [2] });
  });

  it("lässt Prüfen erst zu, wenn etwas gewählt wurde", () => {
    render(<BuildSentenceExercise exercise={build} onSubmit={vi.fn()} />);
    expect(screen.getByRole("button", { name: "Prüfen" })).toBeDisabled();
  });
});

const choose = {
  id: "6-4",
  type: "choose_form" as const,
  prompt_de: "Welche Form von ты passt?",
  sentence: [{ text: "как", translit: "kak" }, null, { text: "зову́т", translit: "zovút" }],
  options: [
    { index: 0, text: "ты", translit: "ty" },
    { index: 1, text: "тебя́", translit: "tebjá" },
  ],
};

describe("ChooseFormExercise", () => {
  it("zeigt die Lücke im Satz", () => {
    render(<ChooseFormExercise exercise={choose} onSubmit={vi.fn()} />);
    expect(screen.getByTestId("blank")).toBeInTheDocument();
  });

  it("meldet den gewählten Index", () => {
    const onSubmit = vi.fn();
    render(<ChooseFormExercise exercise={choose} onSubmit={onSubmit} />);
    fireEvent.click(screen.getByRole("button", { name: /тебя́/ }));
    expect(onSubmit).toHaveBeenCalledWith({ option_index: 1 });
  });
});

const match = {
  id: "5-1",
  type: "match_pairs" as const,
  prompt_de: "Ordne zu.",
  left: [
    { index: 0, text: "приве́т", translit: "privét" },
    { index: 1, text: "пока́", translit: "poká" },
  ],
  right: [
    { index: 0, gloss_de: "tschüss (locker)" },
    { index: 1, gloss_de: "hallo (locker)" },
  ],
};

describe("MatchPairsExercise", () => {
  it("sendet die Paare, sobald alle zugeordnet sind", () => {
    const onSubmit = vi.fn();
    render(<MatchPairsExercise exercise={match} onSubmit={onSubmit} />);
    fireEvent.click(screen.getByRole("button", { name: /приве́т/ }));
    fireEvent.click(screen.getByRole("button", { name: "hallo (locker)" }));
    fireEvent.click(screen.getByRole("button", { name: /пока́/ }));
    fireEvent.click(screen.getByRole("button", { name: "tschüss (locker)" }));
    expect(onSubmit).toHaveBeenCalledWith({ pairs: [[0, 1], [1, 0]] });
  });
});

const dialog = {
  id: "5-6",
  type: "dialog_reply" as const,
  prompt_de: "Was antwortest du?",
  tutor_line: [{ text: "здра́вствуйте", translit: "zdrávstvujte" }],
  options: [
    { index: 0, text: "пока́", translit: "poká" },
    { index: 1, text: "здра́вствуйте", translit: "zdrávstvujte" },
  ],
};

describe("DialogReplyExercise", () => {
  it("zeigt die Tutor-Zeile und meldet die Wahl", () => {
    const onSubmit = vi.fn();
    render(<DialogReplyExercise exercise={dialog} onSubmit={onSubmit} />);
    expect(screen.getByTestId("tutor-line")).toHaveTextContent("здра́вствуйте");
    fireEvent.click(screen.getAllByRole("button", { name: /пока́/ })[0]);
    expect(onSubmit).toHaveBeenCalledWith({ option_index: 0 });
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && npm test -- exercises`
Expected: FAIL — die vier Module fehlen

- [ ] **Step 3: Implement BuildSentenceExercise**

```tsx
// frontend/src/course/BuildSentenceExercise.tsx
import { useState } from "react";

import type { BuildSentenceExercise as Model, Submission } from "../courseTypes";
import Tile from "./Tile";

export default function BuildSentenceExercise({
  exercise,
  disabled = false,
  onSubmit,
}: {
  exercise: Model;
  disabled?: boolean;
  onSubmit: (submission: Submission) => void;
}) {
  const [chosen, setChosen] = useState<number[]>([]);

  const toggle = (index: number) =>
    setChosen((current) =>
      current.includes(index) ? current.filter((item) => item !== index) : [...current, index],
    );

  return (
    <div className="space-y-4">
      <p className="text-lg">{exercise.prompt_de}</p>
      <div className="min-h-16 rounded-xl border-2 border-dashed border-slate-300 p-3">
        <div className="flex flex-wrap gap-2">
          {chosen.map((index) => (
            <Tile
              key={index}
              word={exercise.tiles[index]}
              state="selected"
              disabled={disabled}
              onClick={() => toggle(index)}
            />
          ))}
        </div>
      </div>
      <div className="flex flex-wrap gap-2">
        {exercise.tiles
          .filter((tile) => !chosen.includes(tile.index))
          .map((tile) => (
            <Tile
              key={tile.index}
              word={tile}
              state="idle"
              disabled={disabled}
              onClick={() => toggle(tile.index)}
            />
          ))}
      </div>
      <button
        type="button"
        disabled={disabled || chosen.length === 0}
        onClick={() => onSubmit({ tile_indices: chosen })}
        className="rounded-xl bg-sky-600 px-5 py-2 font-medium text-white disabled:opacity-50"
      >
        Prüfen
      </button>
    </div>
  );
}
```

- [ ] **Step 4: Implement ChooseFormExercise**

```tsx
// frontend/src/course/ChooseFormExercise.tsx
import type { ChooseFormExercise as Model, Submission } from "../courseTypes";
import RussianText from "./RussianText";
import Tile from "./Tile";

export default function ChooseFormExercise({
  exercise,
  disabled = false,
  onSubmit,
}: {
  exercise: Model;
  disabled?: boolean;
  onSubmit: (submission: Submission) => void;
}) {
  return (
    <div className="space-y-4">
      <p className="text-lg">{exercise.prompt_de}</p>
      <div className="flex flex-wrap items-end gap-3 text-xl">
        {exercise.sentence.map((word, position) =>
          word === null ? (
            <span
              key={`blank-${position}`}
              data-testid="blank"
              className="inline-block w-24 border-b-2 border-slate-400"
            />
          ) : (
            <RussianText key={`word-${position}`} word={word} />
          ),
        )}
      </div>
      <div className="flex flex-wrap gap-2">
        {exercise.options.map((option) => (
          <Tile
            key={option.index}
            word={option}
            state="idle"
            disabled={disabled}
            onClick={() => onSubmit({ option_index: option.index })}
          />
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 5: Implement MatchPairsExercise**

```tsx
// frontend/src/course/MatchPairsExercise.tsx
import { useState } from "react";

import type { MatchPairsExercise as Model, Submission } from "../courseTypes";
import Tile from "./Tile";

export default function MatchPairsExercise({
  exercise,
  disabled = false,
  onSubmit,
}: {
  exercise: Model;
  disabled?: boolean;
  onSubmit: (submission: Submission) => void;
}) {
  const [active, setActive] = useState<number | null>(null);
  const [pairs, setPairs] = useState<number[][]>([]);

  const matchedLeft = pairs.map((pair) => pair[0]);
  const matchedRight = pairs.map((pair) => pair[1]);

  const pickRight = (rightIndex: number) => {
    if (active === null) return;
    const next = [...pairs, [active, rightIndex]];
    setPairs(next);
    setActive(null);
    if (next.length === exercise.left.length) {
      onSubmit({ pairs: next });
    }
  };

  return (
    <div className="space-y-4">
      <p className="text-lg">{exercise.prompt_de}</p>
      <div className="grid grid-cols-2 gap-4">
        <div className="flex flex-col gap-2">
          {exercise.left.map((item) => (
            <Tile
              key={item.index}
              word={item}
              state={
                matchedLeft.includes(item.index)
                  ? "correct"
                  : active === item.index
                    ? "selected"
                    : "idle"
              }
              disabled={disabled || matchedLeft.includes(item.index)}
              onClick={() => setActive(item.index)}
            />
          ))}
        </div>
        <div className="flex flex-col gap-2">
          {exercise.right.map((item) => (
            <button
              key={item.index}
              type="button"
              disabled={disabled || matchedRight.includes(item.index)}
              onClick={() => pickRight(item.index)}
              className="rounded-xl border-2 border-slate-300 bg-white px-4 py-2 text-left disabled:opacity-50"
            >
              {item.gloss_de}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 6: Implement DialogReplyExercise and the runner**

```tsx
// frontend/src/course/DialogReplyExercise.tsx
import type { DialogReplyExercise as Model, Submission } from "../courseTypes";
import RussianText from "./RussianText";
import Tile from "./Tile";

export default function DialogReplyExercise({
  exercise,
  disabled = false,
  onSubmit,
}: {
  exercise: Model;
  disabled?: boolean;
  onSubmit: (submission: Submission) => void;
}) {
  return (
    <div className="space-y-4">
      <p className="text-lg">{exercise.prompt_de}</p>
      <div
        data-testid="tutor-line"
        className="flex flex-wrap gap-2 rounded-2xl bg-white p-4 text-xl shadow-sm"
      >
        {exercise.tutor_line.map((word, position) => (
          <RussianText key={position} word={word} />
        ))}
      </div>
      <div className="flex flex-col gap-2">
        {exercise.options.map((option) => (
          <Tile
            key={option.index}
            word={option}
            state="idle"
            disabled={disabled}
            onClick={() => onSubmit({ option_index: option.index })}
          />
        ))}
      </div>
    </div>
  );
}
```

```tsx
// frontend/src/course/ExerciseRunner.tsx
import type { Exercise, Submission } from "../courseTypes";
import BuildSentenceExercise from "./BuildSentenceExercise";
import ChooseFormExercise from "./ChooseFormExercise";
import DialogReplyExercise from "./DialogReplyExercise";
import MatchPairsExercise from "./MatchPairsExercise";

export default function ExerciseRunner({
  exercise,
  disabled = false,
  onSubmit,
}: {
  exercise: Exercise;
  disabled?: boolean;
  onSubmit: (submission: Submission) => void;
}) {
  const props = { disabled, onSubmit };
  switch (exercise.type) {
    case "build_sentence":
      return <BuildSentenceExercise exercise={exercise} {...props} />;
    case "choose_form":
      return <ChooseFormExercise exercise={exercise} {...props} />;
    case "match_pairs":
      return <MatchPairsExercise exercise={exercise} {...props} />;
    case "dialog_reply":
      return <DialogReplyExercise exercise={exercise} {...props} />;
  }
}
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `cd frontend && npm test`
Expected: PASS (7 neue Tests)

- [ ] **Step 8: Commit**

```bash
git add frontend/src/course
git commit -m "feat: add the four click-only exercise components"
```

---
## Task 13: Kursübersicht und Lerneinheit

**Files:**
- Create: `frontend/src/views/CourseView.tsx` (ersetzt den Platzhalter)
- Create: `frontend/src/views/UnitView.tsx` (ersetzt den Platzhalter)
- Test: `frontend/src/views/CourseView.test.tsx`
- Test: `frontend/src/views/UnitView.test.tsx`

**Interfaces:**
- Consumes: `getCourse`, `getUnit`, `submitAnswer` aus `courseApi`; `ExerciseRunner`
- Produces: die beiden Views; `STAGE_TITLES: Record<number, string>` aus `views/CourseView`

Stufenüberschriften: 0 „Schrift & Klang", 1 „Erste Sätze", 2 „Alltag konkret", 3 „Erzählen", 4 „Flüssiger Alltag".

- [ ] **Step 1: Write the failing tests**

```tsx
// frontend/src/views/CourseView.test.tsx
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as api from "../courseApi";
import CourseView from "./CourseView";

const overview = {
  stages: [
    {
      stage: 0,
      units: [
        { id: 1, title_de: "Buchstaben, die täuschen", scenario_de: "…", status: "completed" as const, correct_count: 6, exercise_count: 6 },
      ],
    },
    {
      stage: 1,
      units: [
        { id: 5, title_de: "Hallo und tschüss", scenario_de: "…", status: "not_started" as const, correct_count: 0, exercise_count: 7 },
      ],
    },
  ],
};

describe("CourseView", () => {
  beforeEach(() => vi.restoreAllMocks());

  it("zeigt die Stufen mit ihren Überschriften", async () => {
    vi.spyOn(api, "getCourse").mockResolvedValue(overview);
    render(<MemoryRouter><CourseView /></MemoryRouter>);
    expect(await screen.findByText("Schrift & Klang")).toBeInTheDocument();
    expect(screen.getByText("Erste Sätze")).toBeInTheDocument();
  });

  it("verlinkt jede Einheit", async () => {
    vi.spyOn(api, "getCourse").mockResolvedValue(overview);
    render(<MemoryRouter><CourseView /></MemoryRouter>);
    const link = await screen.findByRole("link", { name: /Hallo und tschüss/ });
    expect(link).toHaveAttribute("href", "/kurs/5");
  });

  it("markiert abgeschlossene Einheiten", async () => {
    vi.spyOn(api, "getCourse").mockResolvedValue(overview);
    render(<MemoryRouter><CourseView /></MemoryRouter>);
    expect(await screen.findByLabelText("Einheit 1: abgeschlossen")).toBeInTheDocument();
  });

  it("zeigt eine deutsche Fehlermeldung, wenn das Laden scheitert", async () => {
    vi.spyOn(api, "getCourse").mockRejectedValue(new Error("kaputt"));
    render(<MemoryRouter><CourseView /></MemoryRouter>);
    expect(await screen.findByText(/konnte nicht geladen werden/i)).toBeInTheDocument();
  });
});
```

```tsx
// frontend/src/views/UnitView.test.tsx
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as api from "../courseApi";
import UnitView from "./UnitView";

const unit = {
  id: 5,
  stage: 1,
  title_de: "Hallo und tschüss",
  scenario_de: "Du triffst jemanden.",
  grammar_focus: { id: "f", title_de: "Locker oder förmlich?", explanation_de: "Zu Fremden sagst du здра́вствуйте." },
  solved_exercise_ids: [],
  exercises: [
    {
      id: "5-3",
      type: "build_sentence" as const,
      prompt_de: "Auf Wiedersehen!",
      tiles: [
        { index: 0, text: "свида́ния", translit: "svidánija" },
        { index: 1, text: "до", translit: "do" },
      ],
    },
    {
      id: "5-4",
      type: "build_sentence" as const,
      prompt_de: "Vielen Dank!",
      tiles: [{ index: 0, text: "спаси́бо", translit: "spasíbo" }],
    },
  ],
};

function renderUnit() {
  return render(
    <MemoryRouter initialEntries={["/kurs/5"]}>
      <Routes>
        <Route path="/kurs/:unitId" element={<UnitView />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("UnitView", () => {
  beforeEach(() => vi.restoreAllMocks());

  it("zeigt zuerst die Regel und startet danach die Aufgaben", async () => {
    vi.spyOn(api, "getUnit").mockResolvedValue(unit);
    renderUnit();
    expect(await screen.findByText("Locker oder förmlich?")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Los geht's" }));
    expect(await screen.findByText("Auf Wiedersehen!")).toBeInTheDocument();
  });

  it("zeigt nach einer falschen Antwort die Lösung", async () => {
    vi.spyOn(api, "getUnit").mockResolvedValue(unit);
    vi.spyOn(api, "submitAnswer").mockResolvedValue({
      correct: false,
      solution_text: "до свида́ния",
      solution_translit: "do svidánija",
      explanation_de: "Richtig ist: до свида́ния",
      unit_completed: false,
      correct_count: 0,
      total_count: 1,
    });
    renderUnit();
    fireEvent.click(await screen.findByRole("button", { name: "Los geht's" }));
    fireEvent.click(await screen.findByRole("button", { name: /свида́ния/ }));
    fireEvent.click(screen.getByRole("button", { name: "Prüfen" }));
    expect(await screen.findByText(/до свида́ния/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Weiter" })).toBeInTheDocument();
  });

  it("zeigt am Ende den Abschluss-Bildschirm", async () => {
    vi.spyOn(api, "getUnit").mockResolvedValue({ ...unit, exercises: [unit.exercises[1]] });
    vi.spyOn(api, "submitAnswer").mockResolvedValue({
      correct: true,
      solution_text: "спаси́бо",
      solution_translit: "spasíbo",
      explanation_de: "",
      unit_completed: true,
      correct_count: 1,
      total_count: 1,
    });
    renderUnit();
    fireEvent.click(await screen.findByRole("button", { name: "Los geht's" }));
    fireEvent.click(await screen.findByRole("button", { name: /спаси́бо/ }));
    fireEvent.click(screen.getByRole("button", { name: "Prüfen" }));
    fireEvent.click(await screen.findByRole("button", { name: "Weiter" }));
    expect(await screen.findByText("Einheit geschafft!")).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && npm test -- views`
Expected: FAIL — die Platzhalter rendern nur eine Überschrift

- [ ] **Step 3: Implement CourseView**

```tsx
// frontend/src/views/CourseView.tsx
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { getCourse } from "../courseApi";
import type { CourseOverview, UnitSummary } from "../courseTypes";

export const STAGE_TITLES: Record<number, string> = {
  0: "Schrift & Klang",
  1: "Erste Sätze",
  2: "Alltag konkret",
  3: "Erzählen",
  4: "Flüssiger Alltag",
};

const STATUS_LABEL: Record<UnitSummary["status"], string> = {
  not_started: "noch offen",
  in_progress: "angefangen",
  completed: "abgeschlossen",
};

const STATUS_STYLE: Record<UnitSummary["status"], string> = {
  not_started: "border-slate-200 bg-white",
  in_progress: "border-sky-300 bg-sky-50",
  completed: "border-emerald-300 bg-emerald-50",
};

export default function CourseView() {
  const [overview, setOverview] = useState<CourseOverview | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    getCourse().then(setOverview).catch(() => setError(true));
  }, []);

  if (error) return <p>Der Kurs konnte nicht geladen werden.</p>;
  if (!overview) return <p>Kurs wird geladen …</p>;

  return (
    <div className="space-y-8">
      {overview.stages.map((stage) => (
        <section key={stage.stage} className="space-y-3">
          <h2 className="text-xl font-semibold">{STAGE_TITLES[stage.stage] ?? `Stufe ${stage.stage}`}</h2>
          <ul className="space-y-2">
            {stage.units.map((unit) => (
              <li key={unit.id}>
                <Link
                  to={`/kurs/${unit.id}`}
                  aria-label={`Einheit ${unit.id}: ${STATUS_LABEL[unit.status]}`}
                  className={`flex items-center justify-between rounded-xl border-2 px-4 py-3 ${STATUS_STYLE[unit.status]}`}
                >
                  <span>
                    <span className="mr-2 text-slate-500">{unit.id}</span>
                    <span className="font-medium">{unit.title_de}</span>
                  </span>
                  <span className="text-sm text-slate-500">{STATUS_LABEL[unit.status]}</span>
                </Link>
              </li>
            ))}
          </ul>
        </section>
      ))}
    </div>
  );
}
```

- [ ] **Step 4: Implement UnitView**

```tsx
// frontend/src/views/UnitView.tsx
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import ExerciseRunner from "../course/ExerciseRunner";
import { getUnit, submitAnswer } from "../courseApi";
import type { AnswerResult, Submission, UnitDetail } from "../courseTypes";

type Phase = "rule" | "exercises" | "done";

export default function UnitView() {
  const { unitId } = useParams();
  const id = Number(unitId);
  const [unit, setUnit] = useState<UnitDetail | null>(null);
  const [phase, setPhase] = useState<Phase>("rule");
  const [position, setPosition] = useState(0);
  const [result, setResult] = useState<AnswerResult | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    getUnit(id).then(setUnit).catch(() => setError(true));
  }, [id]);

  if (error) return <p>Die Einheit konnte nicht geladen werden.</p>;
  if (!unit) return <p>Einheit wird geladen …</p>;

  if (phase === "rule") {
    return (
      <article className="space-y-4">
        <h2 className="text-2xl font-semibold">{unit.title_de}</h2>
        <p className="text-slate-600">{unit.scenario_de}</p>
        <section className="rounded-2xl border-2 border-sky-200 bg-sky-50 p-4">
          <h3 className="font-medium">{unit.grammar_focus.title_de}</h3>
          <p className="mt-2 whitespace-pre-line">{unit.grammar_focus.explanation_de}</p>
        </section>
        <button
          type="button"
          onClick={() => setPhase("exercises")}
          className="rounded-xl bg-sky-600 px-5 py-2 font-medium text-white"
        >
          Los geht's
        </button>
      </article>
    );
  }

  if (phase === "done") {
    return (
      <div className="space-y-4">
        <h2 className="text-2xl font-semibold">Einheit geschafft!</h2>
        <Link to="/kurs" className="inline-block rounded-xl bg-sky-600 px-5 py-2 font-medium text-white">
          Zurück zum Kurs
        </Link>
      </div>
    );
  }

  const exercise = unit.exercises[position];

  const handleSubmit = (submission: Submission) => {
    submitAnswer(id, exercise.id, submission).then(setResult).catch(() => setError(true));
  };

  const advance = () => {
    setResult(null);
    if (position + 1 >= unit.exercises.length) {
      setPhase("done");
    } else {
      setPosition(position + 1);
    }
  };

  return (
    <div className="space-y-6">
      <p className="text-sm text-slate-500">
        Aufgabe {position + 1} von {unit.exercises.length}
      </p>
      <ExerciseRunner
        key={exercise.id}
        exercise={exercise}
        disabled={result !== null}
        onSubmit={handleSubmit}
      />
      {result ? (
        <div
          className={`space-y-2 rounded-2xl p-4 ${result.correct ? "bg-emerald-50" : "bg-rose-50"}`}
        >
          <p className="font-medium">{result.correct ? "Richtig!" : "Nicht ganz."}</p>
          {!result.correct ? (
            <p>
              Richtig ist: <span lang="ru">{result.solution_text}</span>
            </p>
          ) : null}
          {result.explanation_de && !result.correct ? <p>{result.explanation_de}</p> : null}
          <button
            type="button"
            onClick={advance}
            className="rounded-xl bg-sky-600 px-5 py-2 font-medium text-white"
          >
            Weiter
          </button>
        </div>
      ) : null}
    </div>
  );
}
```

- [ ] **Step 5: Keep the shell test isolated from the network**

`CourseView` lädt jetzt wirklich Daten, deshalb muss `frontend/src/App.test.tsx` den Aufruf stubben.
Ergänze dort vor dem `render`:

```tsx
import * as api from "./courseApi";

vi.spyOn(api, "getCourse").mockResolvedValue({ stages: [] });
vi.spyOn(api, "getProfile").mockResolvedValue({
  language: "russian",
  cefr_level: "UNPLACED",
  show_transliteration: true,
  placement_unit: null,
});
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd frontend && npm test`
Expected: PASS (7 neue Tests)

- [ ] **Step 7: Commit**

```bash
git add frontend/src/views frontend/src/App.test.tsx
git commit -m "feat: add course overview and unit runner views"
```

---

## Task 14: Einstufung, Wiederholung und Profil

**Files:**
- Create: `frontend/src/views/ScreeningView.tsx` (ersetzt den Platzhalter)
- Create: `frontend/src/views/ReviewView.tsx` (ersetzt den Platzhalter)
- Modify: `frontend/src/ProfileView.tsx`
- Test: `frontend/src/views/ScreeningView.test.tsx`
- Test: `frontend/src/views/ReviewView.test.tsx`

**Interfaces:**
- Consumes: `startScreening`, `answerScreening`, `getReviewRound`, `submitReviewRound`, `getProfile` aus `courseApi`; `useTransliteration`
- Produces: die beiden Views; `ProfileView` bekommt den Umschrift-Schalter und einen Link zur Einstufung

- [ ] **Step 1: Write the failing tests**

```tsx
// frontend/src/views/ScreeningView.test.tsx
import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as api from "../courseApi";
import ScreeningView from "./ScreeningView";

const probe = {
  id: "s1",
  index: 0,
  total: 6,
  prompt_de: "Welcher Buchstabe klingt wie ein gerolltes r?",
  options: ["Р", "П", "Г"],
};

describe("ScreeningView", () => {
  beforeEach(() => vi.restoreAllMocks());

  it("zeigt die erste Sonde mit Fortschritt", async () => {
    vi.spyOn(api, "startScreening").mockResolvedValue({ finished: false, probe });
    render(<MemoryRouter><ScreeningView /></MemoryRouter>);
    expect(await screen.findByText(probe.prompt_de)).toBeInTheDocument();
    expect(screen.getByText("Frage 1 von 6")).toBeInTheDocument();
  });

  it("schickt die gesammelten Antworten weiter", async () => {
    vi.spyOn(api, "startScreening").mockResolvedValue({ finished: false, probe });
    const answer = vi
      .spyOn(api, "answerScreening")
      .mockResolvedValue({ finished: false, probe: { ...probe, index: 1 } });
    render(<MemoryRouter><ScreeningView /></MemoryRouter>);
    fireEvent.click(await screen.findByRole("button", { name: "П" }));
    expect(answer).toHaveBeenCalledWith([1]);
  });

  it("zeigt am Ende die empfohlene Starteinheit", async () => {
    vi.spyOn(api, "startScreening").mockResolvedValue({ finished: false, probe });
    vi.spyOn(api, "answerScreening").mockResolvedValue({ finished: true, placement_unit: 5 });
    render(<MemoryRouter><ScreeningView /></MemoryRouter>);
    fireEvent.click(await screen.findByRole("button", { name: "Р" }));
    expect(await screen.findByRole("link", { name: /Einheit 5/ })).toHaveAttribute("href", "/kurs/5");
  });
});
```

```tsx
// frontend/src/views/ReviewView.test.tsx
import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as api from "../courseApi";
import ReviewView from "./ReviewView";

const round = {
  left: [
    { index: 0, ref: "privet:base", text: "приве́т", translit: "privét" },
    { index: 1, ref: "poka:base", text: "пока́", translit: "poká" },
  ],
  right: [
    { index: 0, gloss_de: "tschüss (locker)" },
    { index: 1, gloss_de: "hallo (locker)" },
  ],
};

describe("ReviewView", () => {
  beforeEach(() => vi.restoreAllMocks());

  it("meldet, wenn nichts fällig ist", async () => {
    vi.spyOn(api, "getReviewRound").mockResolvedValue({ left: [], right: [] });
    render(<ReviewView />);
    expect(await screen.findByText(/nichts zu wiederholen/i)).toBeInTheDocument();
  });

  it("schickt die Zuordnung ab und zeigt das Ergebnis", async () => {
    vi.spyOn(api, "getReviewRound").mockResolvedValue(round);
    vi.spyOn(api, "submitReviewRound").mockResolvedValue({
      correct_count: 2,
      total_count: 2,
      results: [
        { ref: "privet:base", correct: true, gloss_de: "hallo (locker)", text: "приве́т" },
        { ref: "poka:base", correct: true, gloss_de: "tschüss (locker)", text: "пока́" },
      ],
    });
    render(<ReviewView />);
    fireEvent.click(await screen.findByRole("button", { name: /приве́т/ }));
    fireEvent.click(screen.getByRole("button", { name: "hallo (locker)" }));
    fireEvent.click(screen.getByRole("button", { name: /пока́/ }));
    fireEvent.click(screen.getByRole("button", { name: "tschüss (locker)" }));
    expect(await screen.findByText("2 von 2 richtig")).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && npm test -- views`
Expected: FAIL — die Platzhalter rendern nur eine Überschrift

- [ ] **Step 3: Implement ScreeningView**

```tsx
// frontend/src/views/ScreeningView.tsx
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { answerScreening, startScreening } from "../courseApi";
import type { ScreeningProbe } from "../courseTypes";

export default function ScreeningView() {
  const [probe, setProbe] = useState<ScreeningProbe | null>(null);
  const [answers, setAnswers] = useState<number[]>([]);
  const [placement, setPlacement] = useState<number | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    startScreening()
      .then((step) => (step.finished ? setPlacement(step.placement_unit) : setProbe(step.probe)))
      .catch(() => setError(true));
  }, []);

  const choose = (option: number) => {
    const next = [...answers, option];
    setAnswers(next);
    answerScreening(next)
      .then((step) => {
        if (step.finished) {
          setPlacement(step.placement_unit);
          setProbe(null);
        } else {
          setProbe(step.probe);
        }
      })
      .catch(() => setError(true));
  };

  if (error) return <p>Die Einstufung konnte nicht geladen werden.</p>;

  if (placement !== null) {
    return (
      <div className="space-y-4">
        <h2 className="text-2xl font-semibold">Fertig!</h2>
        <p>Wir schlagen vor, dass du hier einsteigst:</p>
        <Link
          to={`/kurs/${placement}`}
          className="inline-block rounded-xl bg-sky-600 px-5 py-2 font-medium text-white"
        >
          Mit Einheit {placement} starten
        </Link>
      </div>
    );
  }

  if (!probe) return <p>Einstufung wird geladen …</p>;

  return (
    <div className="space-y-4">
      <p className="text-sm text-slate-500">
        Frage {probe.index + 1} von {probe.total}
      </p>
      <h2 className="text-xl">{probe.prompt_de}</h2>
      <div className="flex flex-col gap-2">
        {probe.options.map((option, index) => (
          <button
            key={option}
            type="button"
            onClick={() => choose(index)}
            className="rounded-xl border-2 border-slate-300 bg-white px-4 py-3 text-left text-lg hover:border-sky-400"
          >
            {option}
          </button>
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Implement ReviewView**

```tsx
// frontend/src/views/ReviewView.tsx
import { useEffect, useState } from "react";

import MatchPairsExercise from "../course/MatchPairsExercise";
import { getReviewRound, submitReviewRound } from "../courseApi";
import type { ReviewResult, ReviewRound } from "../courseTypes";

export default function ReviewView() {
  const [round, setRound] = useState<ReviewRound | null>(null);
  const [result, setResult] = useState<ReviewResult | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    getReviewRound().then(setRound).catch(() => setError(true));
  }, []);

  if (error) return <p>Die Wiederholung konnte nicht geladen werden.</p>;
  if (!round) return <p>Wiederholung wird geladen …</p>;

  if (result) {
    return (
      <div className="space-y-3">
        <h2 className="text-2xl font-semibold">
          {result.correct_count} von {result.total_count} richtig
        </h2>
        <ul className="space-y-1">
          {result.results.map((item) => (
            <li key={item.ref} className={item.correct ? "text-emerald-700" : "text-rose-700"}>
              <span lang="ru">{item.text}</span> — {item.gloss_de}
            </li>
          ))}
        </ul>
      </div>
    );
  }

  if (round.left.length === 0) {
    return <p>Gerade gibt es nichts zu wiederholen. Mach im Kurs weiter!</p>;
  }

  return (
    <MatchPairsExercise
      exercise={{
        id: "review",
        type: "match_pairs",
        prompt_de: "Ordne die fälligen Wortformen ihrer Bedeutung zu.",
        left: round.left,
        right: round.right,
      }}
      onSubmit={(submission) => {
        if ("pairs" in submission) {
          submitReviewRound(submission.pairs).then(setResult).catch(() => setError(true));
        }
      }}
    />
  );
}
```

- [ ] **Step 5: Extend ProfileView**

Ergänze in `frontend/src/ProfileView.tsx`:
- einen Schalter „Umschrift anzeigen", der `useTransliteration()` benutzt (`<input type="checkbox" checked={show} onChange={(event) => setShow(event.target.checked)} />` mit Label „Umschrift anzeigen")
- einen `<Link to="/einstufung">Einstufung starten</Link>`
- die Anzeige von `placement_unit` als „Empfohlener Einstieg: Einheit N", falls gesetzt

- [ ] **Step 6: Gate the free-form chat behind stage 3**

Spec §8 verlangt, dass der Freitext-Chat erst ab Stufe 3 erreichbar ist. Umsetzung in `ProfileView`:
lade `getCourse()` und zeige den Link `<Link to="/gespraech">Freies Gespräch</Link>` nur, wenn in
Stufe 3 mindestens eine Einheit den Status `completed` hat. Andernfalls steht dort der Hinweistext
„Freies Gespräch schaltet sich frei, sobald du Stufe 3 erreichst." In der Hauptnavigation taucht der
Chat nicht auf; die Route `/gespraech` bleibt bestehen, damit ein direkter Aufruf funktioniert.

Test dazu in `frontend/src/ProfileView.test.tsx`:

```tsx
it("blendet das freie Gespräch vor Stufe 3 aus", async () => {
  vi.spyOn(api, "getCourse").mockResolvedValue({
    stages: [{ stage: 1, units: [{ id: 5, title_de: "x", scenario_de: "y", status: "completed", correct_count: 7, exercise_count: 7 }] }],
  });
  render(<MemoryRouter><ProfileView /></MemoryRouter>);
  expect(await screen.findByText(/schaltet sich frei/i)).toBeInTheDocument();
});
```

- [ ] **Step 7: Run the full frontend suite**

Run: `cd frontend && npm test`
Expected: PASS — alle Tests, auch die bestehenden

- [ ] **Step 8: Build to catch type errors**

Run: `cd frontend && npx tsc --noEmit && npm run build`
Expected: kein Fehler

- [ ] **Step 9: Commit**

```bash
git add frontend/src
git commit -m "feat: add screening, review and profile settings views"
```

---

## Task 15: Ende-zu-Ende-Rauchtest

**Files:**
- Create: `scripts/smoke_test.sh`
- Modify: `README.md`

- [ ] **Step 1: Write the smoke test script**

```bash
#!/usr/bin/env bash
# scripts/smoke_test.sh — prüft den laufenden docker-compose-Stack.
set -euo pipefail

BASE="${BASE:-http://localhost:8000}"

echo "1/4 Health"
curl -sf "$BASE/api/health" | grep -q '"status":"ok"'

echo "2/4 Kursübersicht"
curl -sf "$BASE/api/course" | grep -q '"stages"'

echo "3/4 Einheit 5"
curl -sf "$BASE/api/units/5" | grep -q '"grammar_focus"'

echo "4/4 Einstufung"
curl -sf -X POST "$BASE/api/screening/start" | grep -q '"probe"'

echo "OK — Backend antwortet auf allen Kurs-Endpunkten."
```

- [ ] **Step 2: Make it executable and run it against the stack**

```bash
chmod +x scripts/smoke_test.sh
docker compose up -d --build
./scripts/smoke_test.sh
```
Expected: `OK — Backend antwortet auf allen Kurs-Endpunkten.`

- [ ] **Step 3: Document the setup in README.md**

Schreibe einen kurzen deutschen Abschnitt: was die App ist, `docker compose up`, die drei Ports, wo der Content liegt, wie man ihn validiert (`python -m scripts.validate_content`), und wie man Backend- und Frontend-Tests startet.

- [ ] **Step 4: Commit**

```bash
git add scripts/smoke_test.sh README.md
git commit -m "chore: add smoke test script and setup documentation"
```

---

## Nach diesem Plan

Die App ist danach mit sechs Einheiten benutzbar. Die Einheiten 7–100 entstehen im Folgeplan
`docs/superpowers/plans/<datum>-russian-course-content.md`: blockweise autoriert, jeweils gegen
`validate_content.py` und `test_real_content.py` geprüft und einzeln committet.
