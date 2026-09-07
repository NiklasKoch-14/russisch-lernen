# Ton und Hörverstehen — Implementierungsplan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Der Russischkurs bekommt Sprachausgabe über die Browser-`SpeechSynthesis` sowie drei Hör-Aufgabenformen, die bei fehlender Stimme sauber auf Text zurückfallen.

**Architecture:** Hör-Aufgaben sind kein eigener Aufgabentyp, sondern ein Schalter `audio_prompt` auf `build_sentence` und `choose_form`; der zu sprechende Text wird serverseitig aus der bereits vorhandenen Lösung abgeleitet. Nur `listen_meaning` (deutsche Antwortoptionen) ist ein echter neuer Typ. Im Frontend liegt eine reine TypeScript-Schicht (`speech.ts`) unter einem React-Context, und jeder Ton wird über genau eine Komponente `SpeakerButton` ausgelöst.

**Tech Stack:** Python 3 / FastAPI / SQLite / pytest im Backend; React 18 / TypeScript / Vite / Vitest / Testing-Library im Frontend; Playwright für e2e.

**Spec:** `docs/superpowers/specs/2026-09-07-speaker-audio-listening-design.md`

## Global Constraints

- Alle Nutzertexte und alle Validator-Meldungen sind **auf Deutsch**.
- Der Grundsatz „nie kyrillisch tippen" gilt weiter: jede Aufgabe bleibt per Klick lösbar.
- **Keine Einheit darf am fehlenden Ton scheitern.** Ohne russische Stimme fällt jede Hör-Aufgabe auf ihre Textform zurück.
- Zwei Größen bleiben streng getrennt: `available` (Stimme vorhanden) steuert den Textrückfall, `audio_autoplay` steuert **ausschließlich** das automatische Abspielen.
- Bestehende Content-Dateien müssen ohne Änderung gültig bleiben — alle neuen Felder sind optional.
- Nach jeder Content-Änderung `make validate`.
- Für eigene Prüfläufe `make test` und `make test-e2e` (headless) benutzen, **nie** `make test-e2e-show` — das öffnet ein Fenster auf dem Desktop des Nutzers.
- Backend-Tests laufen mit `backend/.venv/bin/python -m pytest`, Frontend-Tests mit `npm test --prefix frontend`.

## Dateiübersicht

**Backend — geändert**

| Datei | Verantwortung nach der Änderung |
|---|---|
| `backend/app/content/models.py` | `Form.speak_as`, `audio_prompt` auf zwei Typen, `ListenMeaningExercise` |
| `backend/app/content/loader.py` | liest die neuen Felder, parst den neuen Typ |
| `backend/app/content/validator.py` | Regeln für die neuen Felder, `_exercise_tokens` kennt den neuen Typ |
| `backend/app/course/presenter.py` | liefert `audio_text`, stellt `listen_meaning` dar |
| `backend/app/course/checker.py` | bewertet `listen_meaning` |
| `backend/app/db.py`, `backend/app/repositories/profile_repo.py`, `backend/app/api/schemas.py` | Profilspalte `audio_autoplay` |

**Frontend — neu**

| Datei | Verantwortung |
|---|---|
| `frontend/src/audio/speech.ts` | reine Funktionen: Betonung entfernen, Stimme wählen, sprechen |
| `frontend/src/audio/SpeechContext.tsx` | Zustand `available` / `autoplay`, stellt `speak` bereit |
| `frontend/src/audio/SpeakerButton.tsx` | das einzige Lautsprecher-Symbol der App |
| `frontend/src/audio/AutoplayToggle.tsx` | Schalter in der Kopfzeile |
| `frontend/src/course/AudioPrompt.tsx` | Abspielen + „langsam" über einer Hör-Aufgabe |
| `frontend/src/course/ListenMeaningExercise.tsx` | der neue Aufgabentyp |

**Frontend — geändert:** `App.tsx`, `courseTypes.ts`, `courseApi.ts`, `course/ExerciseRunner.tsx`, `course/BuildSentenceExercise.tsx`, `course/ChooseFormExercise.tsx`, `views/UnitView.tsx`, `views/ReviewView.tsx`, `ProfileView.tsx`

**Nicht angefasst:** `course/Tile.tsx` (ein Lautsprecher darin wäre ein Button im Button) und `VocabView.tsx` (toter Code aus Phase 1 — nirgends importiert, keine Route).

**Content:** `content/ru/lexicon.json`, `content/ru/units/005.json` … `024.json`

---

### Task 1: `speak_as` im Lexikon

Buchstaben sollen ihren Laut hören lassen, nicht ihren Namen — `speechSynthesis` liest `Р р` sonst als „эр".

**Files:**
- Modify: `backend/app/content/models.py` (Dataclass `Form`)
- Modify: `backend/app/content/loader.py` (`_lexeme`)
- Modify: `backend/app/content/validator.py` (`_check_lexicon`)
- Test: `backend/tests/test_content_loader.py`, `backend/tests/test_content_validator.py`

**Interfaces:**
- Consumes: nichts
- Produces: `Form(text: str, translit: str, speak_as: str | None = None)`

- [ ] **Step 1: Write the failing tests**

In `backend/tests/test_content_loader.py` anhängen:

```python
def test_loader_liest_speak_as(tmp_path):
    course = write_and_load(
        tmp_path,
        lexemes=[
            {
                "id": "bu_r",
                "lemma": "Р р",
                "pos": "letter",
                "gloss_de": "gerolltes r",
                "forms": {"base": {"text": "Р р", "translit": "r", "speak_as": "ры́ба"}},
            }
        ],
    )
    assert course.lexemes["bu_r"].forms["base"].speak_as == "ры́ба"


def test_loader_speak_as_ist_optional(tmp_path):
    course = write_and_load(
        tmp_path,
        lexemes=[
            {
                "id": "dom",
                "lemma": "дом",
                "pos": "noun",
                "gloss_de": "Haus",
                "forms": {"nom.sg": {"text": "дом", "translit": "dom"}},
            }
        ],
    )
    assert course.lexemes["dom"].forms["nom.sg"].speak_as is None
```

`write_and_load` ist der bestehende Helfer in dieser Datei; falls er anders heißt, den vorhandenen Aufbaustil der Datei übernehmen und `backend/tests/content_factory.py` benutzen.

In `backend/tests/test_content_validator.py` anhängen:

```python
def test_validator_meldet_leeres_speak_as():
    course = course_with_lexeme_form(speak_as="   ")
    errors = validate_course(course)
    assert any("speak_as" in error for error in errors)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `backend/.venv/bin/python -m pytest tests/test_content_loader.py tests/test_content_validator.py -v` (aus `backend/`)
Expected: FAIL — `Form.__init__() got an unexpected keyword argument 'speak_as'` bzw. keine Meldung zu `speak_as`.

- [ ] **Step 3: Implement**

In `models.py`:

```python
@dataclass(frozen=True)
class Form:
    text: str
    translit: str
    speak_as: str | None = None
```

In `loader.py`, in `_lexeme`:

```python
        forms = {
            key: Form(
                text=value["text"],
                translit=value["translit"],
                speak_as=value.get("speak_as"),
            )
            for key, value in raw["forms"].items()
        }
```

In `validator.py`, in `_check_lexicon` innerhalb der Schleife über die Formen:

```python
            if form.speak_as is not None and not form.speak_as.strip():
                errors.append(
                    f"Lexem {lexeme.id!r}, Form {key!r}: speak_as ist gesetzt, aber leer"
                )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `backend/.venv/bin/python -m pytest -v` (aus `backend/`)
Expected: PASS, alle bestehenden Tests weiterhin grün.

- [ ] **Step 5: Commit**

```bash
git add backend/app/content/models.py backend/app/content/loader.py backend/app/content/validator.py backend/tests/
git commit -m "feat(content): let a form declare what is spoken instead of its text"
```

---

### Task 2: `audio_prompt` und `audio_text`

**Files:**
- Modify: `backend/app/content/models.py`, `loader.py`, `validator.py`
- Modify: `backend/app/course/presenter.py`
- Test: `backend/tests/test_content_loader.py`, `test_content_validator.py`, `test_course_presenter.py`

**Interfaces:**
- Consumes: `Form.speak_as` aus Task 1
- Produces:
  - `BuildSentenceExercise.audio_prompt: bool`, `ChooseFormExercise.audio_prompt: bool`
  - `presenter.spoken_text(course, refs: list[TokenRef]) -> str`
  - `present_exercise` liefert bei gesetztem `audio_prompt` zusätzlich den Schlüssel `audio_text: str`

- [ ] **Step 1: Write the failing tests**

In `backend/tests/test_course_presenter.py`:

```python
def test_spoken_text_nutzt_speak_as_wenn_gesetzt(course_with_letter):
    assert spoken_text(course_with_letter, [("bu_r", "base")]) == "ры́ба"


def test_build_sentence_mit_audio_prompt_liefert_gesprochenen_satz(course):
    exercise = BuildSentenceExercise(
        id="22-4",
        prompt_de="Wie alt bist du?",
        solution=[("skolko", "base"), ("ty", "dat"), ("god", "gen.pl")],
        distractors=[],
        audio_prompt=True,
    )
    payload = present_exercise(course, exercise)
    assert payload["audio_prompt"] is True
    assert payload["audio_text"] == "ско́лько тебе́ лет"


def test_ohne_audio_prompt_kein_audio_text(course):
    exercise = BuildSentenceExercise(
        id="22-4", prompt_de="…", solution=[("ty", "dat")], distractors=[]
    )
    payload = present_exercise(course, exercise)
    assert payload["audio_prompt"] is False
    assert "audio_text" not in payload


def test_choose_form_audio_text_fuellt_die_luecke(course):
    exercise = ChooseFormExercise(
        id="22-5",
        prompt_de="Mein Sohn ist zwei.",
        sentence=[("on", "dat"), ("dva", "nom.m"), None],
        answer=("god", "gen.sg"),
        distractor_forms=["nom.sg", "gen.pl"],
        audio_prompt=True,
    )
    payload = present_exercise(course, exercise)
    assert payload["audio_text"] == "ему́ два го́да"
```

Die `course`-Fixture kommt aus `backend/tests/content_factory.py`; sie muss die benutzten Lexeme enthalten. Fehlen sie, dort ergänzen — die Factory ist genau dafür da.

In `backend/tests/test_content_validator.py`:

```python
def test_validator_verbietet_audio_prompt_auf_match_pairs():
    course = course_with_exercise(
        MatchPairsExercise(id="9-1", prompt_de="…", pairs=[("dom", "nom.sg"), ("ty", "nom")])
    )
    # match_pairs kennt das Feld nicht — der Loader muss es ablehnen
    with pytest.raises(ContentError, match="audio_prompt"):
        load_exercise({"id": "9-1", "type": "match_pairs", "prompt_de": "…",
                       "pairs": [["dom", "nom.sg"]], "audio_prompt": True}, unit_id=9)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `backend/.venv/bin/python -m pytest tests/test_course_presenter.py tests/test_content_validator.py -v`
Expected: FAIL — `audio_prompt` ist kein Feld, `spoken_text` existiert nicht.

- [ ] **Step 3: Implement**

In `models.py` je ein Feld ergänzen (ans Ende **vor** `type`, weil `type` einen Default hat — beide brauchen Defaults):

```python
@dataclass(frozen=True)
class BuildSentenceExercise:
    id: str
    prompt_de: str
    solution: list[TokenRef]
    distractors: list[TokenRef]
    audio_prompt: bool = False
    type: str = "build_sentence"


@dataclass(frozen=True)
class ChooseFormExercise:
    id: str
    prompt_de: str
    sentence: list[TokenRef | None]
    answer: TokenRef
    distractor_forms: list[str]
    audio_prompt: bool = False
    type: str = "choose_form"
```

In `loader.py` in `_exercise` bei beiden Zweigen `audio_prompt=bool(raw.get("audio_prompt", False))` ergänzen. Zusätzlich am Anfang von `_exercise`, damit das Feld nicht still auf einem falschen Typ landet:

```python
    if "audio_prompt" in raw and kind not in ("build_sentence", "choose_form"):
        raise ContentError(
            f"{where}: audio_prompt gibt es nur bei build_sentence und choose_form,"
            f" nicht bei {kind!r}"
        )
```

In `presenter.py`:

```python
def spoken_text(course: Course, refs: list[TokenRef]) -> str:
    """The sentence as it should be read aloud — speak_as wins over the written form."""
    parts = []
    for ref in refs:
        form = course.form(ref)
        parts.append(form.speak_as or form.text)
    return " ".join(parts)


def _filled_sentence(exercise: ChooseFormExercise) -> list[TokenRef]:
    """The choose_form sentence with the answer in the blank."""
    return [exercise.answer if ref is None else ref for ref in exercise.sentence]
```

In `present_exercise` im `BuildSentenceExercise`-Zweig:

```python
        payload = base | {
            "tiles": [{"index": index, **_word(course, ref)} for index, ref in enumerate(tiles)],
            "audio_prompt": exercise.audio_prompt,
        }
        if exercise.audio_prompt:
            payload["audio_text"] = spoken_text(course, list(exercise.solution))
        return payload
```

und analog im `ChooseFormExercise`-Zweig mit `spoken_text(course, _filled_sentence(exercise))`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `backend/.venv/bin/python -m pytest -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/content backend/app/course/presenter.py backend/tests/
git commit -m "feat(course): derive spoken audio from the solution behind an audio_prompt flag"
```

---

### Task 3: Aufgabentyp `listen_meaning`

**Files:**
- Modify: `backend/app/content/models.py`, `loader.py`, `validator.py`
- Modify: `backend/app/course/presenter.py`, `backend/app/course/checker.py`
- Test: `backend/tests/test_content_loader.py`, `test_content_validator.py`, `test_course_presenter.py`, `test_course_checker.py`

**Interfaces:**
- Consumes: `spoken_text` aus Task 2, `shuffled_order` aus `app.course.shuffle`
- Produces:
  - `ListenMeaningExercise(id, prompt_de, sentence: list[TokenRef], options_de: list[str], correct_index: int, type="listen_meaning")`
  - `presenter.listen_meaning_options(course, exercise) -> list[int]` (Original-Indizes in Anzeigereihenfolge)
  - Darstellung: `{id, type, prompt_de, audio_text, sentence, options_de}`
  - Einreichung: `{"option_index": <Anzeige-Index>}`

- [ ] **Step 1: Write the failing tests**

`backend/tests/test_course_checker.py`:

```python
def test_listen_meaning_akzeptiert_die_richtige_option(course):
    exercise = ListenMeaningExercise(
        id="25-7",
        prompt_de="Hör zu. Was wird gesagt?",
        sentence=[("ja", "nom"), ("zhit", "prs.1sg")],
        options_de=["Ich wohne.", "Er wohnt.", "Ich fahre."],
        correct_index=0,
    )
    order = listen_meaning_options(course, exercise)
    display_index = order.index(0)
    result = check_answer(course, exercise, {"option_index": display_index})
    assert result.correct
    assert result.trained_forms == [("ja", "nom"), ("zhit", "prs.1sg")]


def test_listen_meaning_lehnt_falsche_option_ab(course):
    exercise = ListenMeaningExercise(
        id="25-7",
        prompt_de="Hör zu.",
        sentence=[("ja", "nom")],
        options_de=["Ich.", "Er.", "Sie."],
        correct_index=0,
    )
    order = listen_meaning_options(course, exercise)
    display_index = order.index(2)
    result = check_answer(course, exercise, {"option_index": display_index})
    assert not result.correct
    assert "Ich." in result.explanation_de


def test_listen_meaning_wertet_muell_als_falsch(course):
    exercise = ListenMeaningExercise(
        id="25-7", prompt_de="…", sentence=[("ja", "nom")],
        options_de=["a", "b", "c"], correct_index=0,
    )
    assert not check_answer(course, exercise, {"option_index": 99}).correct
    assert not check_answer(course, exercise, {}).correct
```

`backend/tests/test_course_presenter.py`:

```python
def test_listen_meaning_mischt_die_optionen_und_verraet_nichts(course):
    exercise = ListenMeaningExercise(
        id="25-7", prompt_de="Hör zu.", sentence=[("ja", "nom")],
        options_de=["Ich.", "Er.", "Sie."], correct_index=0,
    )
    payload = present_exercise(course, exercise)
    assert sorted(payload["options_de"]) == ["Er.", "Ich.", "Sie."]
    assert "correct_index" not in payload
    assert payload["audio_text"] == "я"
```

`backend/tests/test_content_validator.py`:

```python
def test_validator_meldet_zu_wenige_optionen():
    unit = unit_with(ListenMeaningExercise(
        id="25-7", prompt_de="…", sentence=[("ja", "nom")],
        options_de=["Ich.", "Er."], correct_index=0))
    assert any("mindestens 3" in error for error in validate_course(course_with(unit)))


def test_validator_meldet_correct_index_ausserhalb():
    unit = unit_with(ListenMeaningExercise(
        id="25-7", prompt_de="…", sentence=[("ja", "nom")],
        options_de=["a", "b", "c"], correct_index=5))
    assert any("correct_index" in error for error in validate_course(course_with(unit)))


def test_validator_meldet_doppelte_optionen():
    unit = unit_with(ListenMeaningExercise(
        id="25-7", prompt_de="…", sentence=[("ja", "nom")],
        options_de=["Ich.", "Ich.", "Er."], correct_index=0))
    assert any("doppelt" in error for error in validate_course(course_with(unit)))


def test_validator_meldet_leeren_satz():
    unit = unit_with(ListenMeaningExercise(
        id="25-7", prompt_de="…", sentence=[], options_de=["a", "b", "c"], correct_index=0))
    assert any("sentence" in error for error in validate_course(course_with(unit)))
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `backend/.venv/bin/python -m pytest -v`
Expected: FAIL — `ListenMeaningExercise` und `listen_meaning_options` existieren nicht.

- [ ] **Step 3: Implement**

`models.py`:

```python
@dataclass(frozen=True)
class ListenMeaningExercise:
    id: str
    prompt_de: str
    sentence: list[TokenRef]
    options_de: list[str]
    correct_index: int
    type: str = "listen_meaning"


Exercise = (
    BuildSentenceExercise
    | ChooseFormExercise
    | MatchPairsExercise
    | DialogReplyExercise
    | ListenMeaningExercise
)
```

`loader.py`, in `_exercise`:

```python
        if kind == "listen_meaning":
            return ListenMeaningExercise(
                id=raw["id"],
                prompt_de=raw["prompt_de"],
                sentence=_tokens(raw["sentence"], where),
                options_de=[str(option) for option in raw["options_de"]],
                correct_index=int(raw["correct_index"]),
            )
```

`presenter.py`:

```python
def listen_meaning_options(course: Course, exercise: ListenMeaningExercise) -> list[int]:
    """Original option indices in display order."""
    return shuffled_order(exercise.id, len(exercise.options_de))
```

und in `present_exercise`:

```python
    if isinstance(exercise, ListenMeaningExercise):
        order = listen_meaning_options(course, exercise)
        return base | {
            "audio_text": spoken_text(course, list(exercise.sentence)),
            "sentence": [_word(course, ref) for ref in exercise.sentence],
            "options_de": [exercise.options_de[original] for original in order],
        }
```

`checker.py`:

```python
def _check_listen_meaning(
    course: Course, exercise: ListenMeaningExercise, submission: dict
) -> CheckResult:
    order = listen_meaning_options(course, exercise)
    index = submission.get("option_index")
    original = order[index] if isinstance(index, int) and 0 <= index < len(order) else None
    text, translit = _render(course, list(exercise.sentence))
    correct = original == exercise.correct_index
    return CheckResult(
        correct=correct,
        solution_text=text,
        solution_translit=translit,
        explanation_de=(
            "" if correct else f"Gesagt wurde: {exercise.options_de[exercise.correct_index]}"
        ),
        trained_forms=list(exercise.sentence),
    )
```

sowie der Zweig in `check_answer` und der Import von `listen_meaning_options`.

`validator.py`, in `_exercise_tokens` **vor** dem `return []`:

```python
    if isinstance(exercise, ListenMeaningExercise):
        return list(exercise.sentence)
```

und in `_check_exercise`:

```python
    if isinstance(exercise, ListenMeaningExercise):
        if len(exercise.options_de) < 3:
            errors.append(f"{where}: braucht mindestens 3 Optionen in options_de")
        if not 0 <= exercise.correct_index < len(exercise.options_de):
            errors.append(
                f"{where}: correct_index {exercise.correct_index} liegt außerhalb der Optionen"
            )
        cleaned = [option.strip() for option in exercise.options_de]
        if any(not option for option in cleaned):
            errors.append(f"{where}: eine Option in options_de ist leer")
        if len(set(cleaned)) != len(cleaned):
            errors.append(f"{where}: zwei Optionen in options_de sind doppelt")
        if not exercise.sentence:
            errors.append(f"{where}: sentence ist leer")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `backend/.venv/bin/python -m pytest -v` und `make validate`
Expected: PASS; `make validate` meldet weiterhin keine Fehler im bestehenden Content.

- [ ] **Step 5: Commit**

```bash
git add backend/app backend/tests/
git commit -m "feat(course): add listen_meaning exercise type"
```

---

### Task 4: Profilspalte `audio_autoplay`

**Files:**
- Modify: `backend/app/db.py:105-108`, `backend/app/repositories/profile_repo.py`, `backend/app/api/schemas.py`, `backend/app/api/routes.py`
- Test: `backend/tests/test_profile_repo.py`, `backend/tests/test_db_migration.py`, `backend/tests/test_course_routes.py`

**Interfaces:**
- Produces: `Profile.audio_autoplay: bool = True`; `GET /api/profile` liefert `audio_autoplay`; `PATCH /api/profile` akzeptiert `audio_autoplay`

- [ ] **Step 1: Write the failing tests**

`backend/tests/test_profile_repo.py`:

```python
def test_profil_hat_autoplay_standardmaessig_an(conn):
    profile = get_or_create_profile(conn, default_language="russian")
    assert profile.audio_autoplay is True


def test_autoplay_laesst_sich_abschalten(conn):
    get_or_create_profile(conn, default_language="russian")
    updated = update_profile(conn, audio_autoplay=False)
    assert updated.audio_autoplay is False
    assert get_or_create_profile(conn, default_language="russian").audio_autoplay is False


def test_autoplay_bleibt_bei_anderen_aenderungen_erhalten(conn):
    get_or_create_profile(conn, default_language="russian")
    update_profile(conn, audio_autoplay=False)
    update_profile(conn, show_transliteration=False)
    assert get_or_create_profile(conn, default_language="russian").audio_autoplay is False
```

`backend/tests/test_db_migration.py` — dem bestehenden Muster für `show_transliteration` folgen: eine Datenbank ohne die Spalte anlegen, `init_db` erneut laufen lassen, prüfen dass `audio_autoplay` existiert und auf 1 steht.

- [ ] **Step 2: Run tests to verify they fail**

Run: `backend/.venv/bin/python -m pytest tests/test_profile_repo.py tests/test_db_migration.py -v`
Expected: FAIL — `Profile` hat kein Feld `audio_autoplay`.

- [ ] **Step 3: Implement**

`db.py` — in `PROFILE_COLUMNS` aufnehmen (die Migration `_ensure_profile_columns` erledigt Bestandsdatenbanken von selbst) und zusätzlich in das `CREATE TABLE profile` am Anfang der Datei:

```python
PROFILE_COLUMNS = {
    "show_transliteration": "INTEGER NOT NULL DEFAULT 1",
    "placement_unit": "INTEGER",
    "audio_autoplay": "INTEGER NOT NULL DEFAULT 1",
}
```

`profile_repo.py`: `SELECT_COLUMNS` um `audio_autoplay` erweitern, Feld `audio_autoplay: bool = True` in die Dataclass, `_row_to_profile` um `audio_autoplay=bool(row["audio_autoplay"])`, das `INSERT` um die Spalte mit Wert `1`, und in `update_profile` Parameter plus `UPDATE`-Spalte nach demselben Muster wie `show_transliteration`.

`schemas.py`: `audio_autoplay: bool = True` in `ProfileResponse`, `audio_autoplay: bool | None = None` in `ProfilePatchRequest`. In `routes.py` den Wert im `PATCH`-Handler durchreichen.

- [ ] **Step 4: Run tests to verify they pass**

Run: `backend/.venv/bin/python -m pytest -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app backend/tests/
git commit -m "feat(profile): store whether audio plays automatically"
```

---

### Task 5: `speech.ts`

**Files:**
- Create: `frontend/src/audio/speech.ts`
- Test: `frontend/src/audio/speech.test.ts`

**Interfaces:**
- Produces:
  - `stripStress(text: string): string`
  - `pickRussianVoice(voices: SpeechSynthesisVoice[]): SpeechSynthesisVoice | null`
  - `loadVoices(): Promise<SpeechSynthesisVoice[]>`
  - `speak(text: string, voice: SpeechSynthesisVoice, rate?: number): void`
  - `NORMAL_RATE = 0.85`, `SLOW_RATE = 0.6`

- [ ] **Step 1: Write the failing test**

`frontend/src/audio/speech.test.ts`:

```ts
import { describe, expect, it, vi } from "vitest";

import { NORMAL_RATE, SLOW_RATE, loadVoices, pickRussianVoice, speak, stripStress } from "./speech";

const voice = (lang: string, name = lang) => ({ lang, name }) as SpeechSynthesisVoice;

describe("stripStress", () => {
  it("entfernt das kombinierende Betonungszeichen", () => {
    expect(stripStress("де́лаю")).toBe("делаю");
  });

  it("lässt ё unangetastet", () => {
    expect(stripStress("ещё")).toBe("ещё");
  });

  it("lässt Text ohne Betonung unverändert", () => {
    expect(stripStress("дом")).toBe("дом");
  });
});

describe("pickRussianVoice", () => {
  it("bevorzugt ru-RU", () => {
    expect(pickRussianVoice([voice("de-DE"), voice("ru"), voice("ru-RU")])?.lang).toBe("ru-RU");
  });

  it("nimmt sonst irgendeine russische Stimme", () => {
    expect(pickRussianVoice([voice("de-DE"), voice("ru")])?.lang).toBe("ru");
  });

  it("gibt null zurück, wenn keine russische Stimme da ist", () => {
    expect(pickRussianVoice([voice("de-DE"), voice("en-US")])).toBeNull();
  });
});

describe("loadVoices", () => {
  it("wartet auf voiceschanged, wenn die Liste zuerst leer ist", async () => {
    let handler: (() => void) | null = null;
    let voices: SpeechSynthesisVoice[] = [];
    vi.stubGlobal("speechSynthesis", {
      getVoices: () => voices,
      addEventListener: (_: string, callback: () => void) => {
        handler = callback;
      },
      removeEventListener: () => {},
    });

    const pending = loadVoices();
    voices = [voice("ru-RU")];
    handler?.();

    expect((await pending).map((item) => item.lang)).toEqual(["ru-RU"]);
  });
});

describe("speak", () => {
  it("bricht laufende Ausgabe ab und spricht ohne Betonungszeichen", () => {
    const cancel = vi.fn();
    const speakSpy = vi.fn();
    vi.stubGlobal("speechSynthesis", { cancel, speak: speakSpy, getVoices: () => [] });
    vi.stubGlobal(
      "SpeechSynthesisUtterance",
      class {
        text: string;
        lang = "";
        rate = 1;
        voice: SpeechSynthesisVoice | null = null;
        constructor(text: string) {
          this.text = text;
        }
      },
    );

    speak("де́лаю", voice("ru-RU"), SLOW_RATE);

    expect(cancel).toHaveBeenCalled();
    expect(speakSpy.mock.calls[0][0]).toMatchObject({ text: "делаю", rate: SLOW_RATE });
  });

  it("benutzt das normale Tempo als Standard", () => {
    const speakSpy = vi.fn();
    vi.stubGlobal("speechSynthesis", { cancel: vi.fn(), speak: speakSpy, getVoices: () => [] });
    vi.stubGlobal(
      "SpeechSynthesisUtterance",
      class {
        text: string;
        lang = "";
        rate = 1;
        voice: SpeechSynthesisVoice | null = null;
        constructor(text: string) {
          this.text = text;
        }
      },
    );

    speak("дом", voice("ru-RU"));

    expect(speakSpy.mock.calls[0][0].rate).toBe(NORMAL_RATE);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test --prefix frontend -- speech`
Expected: FAIL — `Cannot find module './speech'`.

- [ ] **Step 3: Implement**

`frontend/src/audio/speech.ts`:

```ts
/** Kombinierendes Akut — steht im Content zur Betonung, verwirrt aber manche Stimmen. */
const COMBINING_ACUTE = "́";

export const NORMAL_RATE = 0.85;
export const SLOW_RATE = 0.6;

export function stripStress(text: string): string {
  return text.replaceAll(COMBINING_ACUTE, "");
}

export function pickRussianVoice(
  voices: SpeechSynthesisVoice[],
): SpeechSynthesisVoice | null {
  return (
    voices.find((voice) => voice.lang === "ru-RU") ??
    voices.find((voice) => voice.lang.toLowerCase().startsWith("ru")) ??
    null
  );
}

/** getVoices() ist beim ersten Aufruf oft leer; die Liste kommt erst mit voiceschanged. */
export function loadVoices(): Promise<SpeechSynthesisVoice[]> {
  if (typeof speechSynthesis === "undefined") return Promise.resolve([]);

  const immediate = speechSynthesis.getVoices();
  if (immediate.length > 0) return Promise.resolve(immediate);

  return new Promise((resolve) => {
    const onChange = () => {
      speechSynthesis.removeEventListener("voiceschanged", onChange);
      resolve(speechSynthesis.getVoices());
    };
    speechSynthesis.addEventListener("voiceschanged", onChange);
  });
}

export function speak(
  text: string,
  voice: SpeechSynthesisVoice,
  rate: number = NORMAL_RATE,
): void {
  speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(stripStress(text));
  utterance.voice = voice;
  utterance.lang = voice.lang;
  utterance.rate = rate;
  speechSynthesis.speak(utterance);
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npm test --prefix frontend -- speech`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/audio/
git commit -m "feat(audio): add speech helpers for stress stripping and voice selection"
```

---

### Task 6: `SpeechContext`

**Files:**
- Create: `frontend/src/audio/SpeechContext.tsx`
- Modify: `frontend/src/courseTypes.ts` (Profile), `frontend/src/courseApi.ts` (`patchProfile`-Signatur), `frontend/src/App.tsx`
- Test: `frontend/src/audio/SpeechContext.test.tsx`

**Interfaces:**
- Consumes: `speech.ts` aus Task 5, `getProfile`/`patchProfile` aus `courseApi`
- Produces: `useSpeech(): { available: boolean | null; autoplay: boolean; setAutoplay(v: boolean): void; say(text: string, opts?: { slow?: boolean }): void }`

- [ ] **Step 1: Write the failing test**

`frontend/src/audio/SpeechContext.test.tsx` — ein Prüf-Component, das `useSpeech` benutzt:

```tsx
import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { SpeechProvider, useSpeech } from "./SpeechContext";

vi.mock("../courseApi", () => ({
  getProfile: vi.fn(() =>
    Promise.resolve({
      language: "russian",
      cefr_level: "A1",
      show_transliteration: true,
      placement_unit: null,
      audio_autoplay: true,
    }),
  ),
  patchProfile: vi.fn(() => Promise.resolve()),
}));

function Probe() {
  const { available, autoplay } = useSpeech();
  return <p>{`${available}-${autoplay}`}</p>;
}

const stubVoices = (langs: string[]) => {
  vi.stubGlobal("speechSynthesis", {
    getVoices: () => langs.map((lang) => ({ lang, name: lang })),
    addEventListener: () => {},
    removeEventListener: () => {},
    cancel: () => {},
    speak: () => {},
  });
};

beforeEach(() => {
  vi.unstubAllGlobals();
});

describe("SpeechProvider", () => {
  it("meldet available=true, wenn eine russische Stimme da ist", async () => {
    stubVoices(["de-DE", "ru-RU"]);
    render(
      <SpeechProvider>
        <Probe />
      </SpeechProvider>,
    );
    await waitFor(() => expect(screen.getByText("true-true")).toBeInTheDocument());
  });

  it("meldet available=false ohne russische Stimme", async () => {
    stubVoices(["de-DE"]);
    render(
      <SpeechProvider>
        <Probe />
      </SpeechProvider>,
    );
    await waitFor(() => expect(screen.getByText("false-true")).toBeInTheDocument());
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test --prefix frontend -- SpeechContext`
Expected: FAIL — Modul existiert nicht.

- [ ] **Step 3: Implement**

`frontend/src/audio/SpeechContext.tsx`:

```tsx
import { createContext, useContext, useEffect, useState } from "react";
import type { ReactNode } from "react";

import { getProfile, patchProfile } from "../courseApi";
import { NORMAL_RATE, SLOW_RATE, loadVoices, pickRussianVoice, speak } from "./speech";

interface SpeechValue {
  /** null, solange die Stimmen noch geladen werden. */
  available: boolean | null;
  autoplay: boolean;
  setAutoplay: (value: boolean) => void;
  say: (text: string, options?: { slow?: boolean }) => void;
}

const SpeechContext = createContext<SpeechValue>({
  available: false,
  autoplay: true,
  setAutoplay: () => {},
  say: () => {},
});

export function useSpeech(): SpeechValue {
  return useContext(SpeechContext);
}

export function SpeechProvider({ children }: { children: ReactNode }) {
  const [voice, setVoice] = useState<SpeechSynthesisVoice | null>(null);
  const [available, setAvailable] = useState<boolean | null>(null);
  const [autoplay, setAutoplayState] = useState(true);

  useEffect(() => {
    let cancelled = false;
    loadVoices().then((voices) => {
      if (cancelled) return;
      const found = pickRussianVoice(voices);
      setVoice(found);
      setAvailable(found !== null);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    getProfile()
      .then((profile) => setAutoplayState(profile.audio_autoplay))
      .catch(() => setAutoplayState(true));
  }, []);

  const setAutoplay = (value: boolean) => {
    setAutoplayState(value);
    patchProfile({ audio_autoplay: value }).catch(() => {});
  };

  const say = (text: string, options?: { slow?: boolean }) => {
    if (!voice) return;
    speak(text, voice, options?.slow ? SLOW_RATE : NORMAL_RATE);
  };

  return (
    <SpeechContext.Provider value={{ available, autoplay, setAutoplay, say }}>
      {children}
    </SpeechContext.Provider>
  );
}
```

In `courseTypes.ts` das Feld `audio_autoplay: boolean;` an `Profile` anhängen. In `courseApi.ts` die `patchProfile`-Signatur erweitern:

```ts
export const patchProfile = (
  patch: Partial<Pick<Profile, "show_transliteration" | "audio_autoplay">>,
) =>
```

In `App.tsx` den `SpeechProvider` **innerhalb** von `TransliterationProvider` um den Rest legen.

Bestehende Tests, die `getProfile` mocken (`App.test.tsx`, `ProfileView.test.tsx`), brauchen `audio_autoplay: true` im Mock-Profil — sonst schlagen sie mit `undefined` fehl.

- [ ] **Step 4: Run tests to verify they pass**

Run: `npm test --prefix frontend`
Expected: PASS, alle bestehenden Tests grün.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/audio/ frontend/src/App.tsx frontend/src/courseTypes.ts frontend/src/courseApi.ts frontend/src/App.test.tsx frontend/src/ProfileView.test.tsx
git commit -m "feat(audio): provide voice availability and autoplay through a context"
```

---

### Task 7: `SpeakerButton`

**Files:**
- Create: `frontend/src/audio/SpeakerButton.tsx`
- Test: `frontend/src/audio/SpeakerButton.test.tsx`

**Interfaces:**
- Consumes: `useSpeech` aus Task 6
- Produces: `<SpeakerButton text={string} label?={string} slow?={boolean} />` — rendert nichts, wenn keine Stimme da ist

- [ ] **Step 1: Write the failing test**

```tsx
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import SpeakerButton from "./SpeakerButton";
import * as context from "./SpeechContext";

const useSpeechAs = (available: boolean | null, say = vi.fn()) => {
  vi.spyOn(context, "useSpeech").mockReturnValue({
    available,
    autoplay: true,
    setAutoplay: vi.fn(),
    say,
  });
  return say;
};

describe("SpeakerButton", () => {
  it("spricht den Text beim Klick", () => {
    const say = useSpeechAs(true);
    render(<SpeakerButton text="де́лаю" />);
    fireEvent.click(screen.getByRole("button", { name: "Anhören" }));
    expect(say).toHaveBeenCalledWith("де́лаю", { slow: false });
  });

  it("spricht langsam, wenn slow gesetzt ist", () => {
    const say = useSpeechAs(true);
    render(<SpeakerButton text="де́лаю" slow label="Langsam anhören" />);
    fireEvent.click(screen.getByRole("button", { name: "Langsam anhören" }));
    expect(say).toHaveBeenCalledWith("де́лаю", { slow: true });
  });

  it("erscheint gar nicht, wenn keine Stimme da ist", () => {
    useSpeechAs(false);
    render(<SpeakerButton text="де́лаю" />);
    expect(screen.queryByRole("button")).toBeNull();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test --prefix frontend -- SpeakerButton`
Expected: FAIL — Modul existiert nicht.

- [ ] **Step 3: Implement**

```tsx
import { useSpeech } from "./SpeechContext";

export default function SpeakerButton({
  text,
  label = "Anhören",
  slow = false,
}: {
  text: string;
  label?: string;
  slow?: boolean;
}) {
  const { available, say } = useSpeech();
  if (!available) return null;

  return (
    <button
      type="button"
      aria-label={label}
      title={label}
      onClick={() => say(text, { slow })}
      className="rounded-full border border-slate-300 px-2 py-1 text-slate-600 hover:border-sky-400 hover:text-sky-700"
    >
      {slow ? "🐢" : "🔊"}
    </button>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npm test --prefix frontend -- SpeakerButton`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/audio/
git commit -m "feat(audio): add the speaker button used everywhere sound is offered"
```

---

### Task 8: `AutoplayToggle` in der Kopfzeile

**Files:**
- Create: `frontend/src/audio/AutoplayToggle.tsx`
- Modify: `frontend/src/App.tsx`
- Test: `frontend/src/audio/AutoplayToggle.test.tsx`

**Interfaces:**
- Consumes: `useSpeech` aus Task 6
- Produces: `<AutoplayToggle />`

- [ ] **Step 1: Write the failing test**

```tsx
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import AutoplayToggle from "./AutoplayToggle";
import * as context from "./SpeechContext";

const mockSpeech = (available: boolean | null, autoplay: boolean) => {
  const setAutoplay = vi.fn();
  vi.spyOn(context, "useSpeech").mockReturnValue({
    available,
    autoplay,
    setAutoplay,
    say: vi.fn(),
  });
  return setAutoplay;
};

describe("AutoplayToggle", () => {
  it("schaltet die Automatik aus", () => {
    const setAutoplay = mockSpeech(true, true);
    render(<AutoplayToggle />);
    fireEvent.click(screen.getByRole("button", { name: "Automatisches Vorlesen ausschalten" }));
    expect(setAutoplay).toHaveBeenCalledWith(false);
  });

  it("schaltet die Automatik wieder ein", () => {
    const setAutoplay = mockSpeech(true, false);
    render(<AutoplayToggle />);
    fireEvent.click(screen.getByRole("button", { name: "Automatisches Vorlesen einschalten" }));
    expect(setAutoplay).toHaveBeenCalledWith(true);
  });

  it("ist ohne Stimme deaktiviert", () => {
    mockSpeech(false, true);
    render(<AutoplayToggle />);
    expect(screen.getByRole("button")).toBeDisabled();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test --prefix frontend -- AutoplayToggle`
Expected: FAIL — Modul existiert nicht.

- [ ] **Step 3: Implement**

```tsx
import { useSpeech } from "./SpeechContext";

export default function AutoplayToggle() {
  const { available, autoplay, setAutoplay } = useSpeech();
  const label = autoplay
    ? "Automatisches Vorlesen ausschalten"
    : "Automatisches Vorlesen einschalten";

  return (
    <button
      type="button"
      aria-label={label}
      aria-pressed={autoplay}
      title={available ? label : "Keine russische Stimme gefunden"}
      disabled={!available}
      onClick={() => setAutoplay(!autoplay)}
      className="rounded-full border border-slate-300 px-2 py-1 disabled:opacity-40"
    >
      {autoplay ? "🔊" : "🔇"}
    </button>
  );
}
```

In `App.tsx` in die Kopfzeile, hinter das `<nav>`:

```tsx
            <div className="ml-auto">
              <AutoplayToggle />
            </div>
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npm test --prefix frontend`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/audio/ frontend/src/App.tsx
git commit -m "feat(audio): toggle automatic playback from the header"
```

---

### Task 9: Hör-Prompt in `build_sentence` und `choose_form`

**Files:**
- Create: `frontend/src/course/AudioPrompt.tsx`
- Modify: `frontend/src/courseTypes.ts`, `frontend/src/course/BuildSentenceExercise.tsx`, `frontend/src/course/ChooseFormExercise.tsx`
- Test: `frontend/src/course/AudioPrompt.test.tsx`, `frontend/src/course/exercises.test.tsx`

**Interfaces:**
- Consumes: `SpeakerButton` (Task 7), `useSpeech` (Task 6)
- Produces: `<AudioPrompt text={string} promptDe={string} />` — bei vorhandener Stimme Lautsprecher + „langsam" und **kein** deutscher Prompt; ohne Stimme nur der deutsche Prompt
- Typen: `BuildSentenceExercise` und `ChooseFormExercise` bekommen `audio_prompt: boolean` und `audio_text?: string`

- [ ] **Step 1: Write the failing tests**

`frontend/src/course/AudioPrompt.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import * as context from "../audio/SpeechContext";
import AudioPrompt from "./AudioPrompt";

const mockSpeech = (available: boolean | null, autoplay = true) => {
  const say = vi.fn();
  vi.spyOn(context, "useSpeech").mockReturnValue({
    available,
    autoplay,
    setAutoplay: vi.fn(),
    say,
  });
  return say;
};

describe("AudioPrompt", () => {
  it("verbirgt den deutschen Prompt, wenn eine Stimme da ist", () => {
    mockSpeech(true);
    render(<AudioPrompt text="ско́лько тебе́ лет" promptDe="Wie alt bist du?" />);
    expect(screen.queryByText("Wie alt bist du?")).toBeNull();
    expect(screen.getByRole("button", { name: "Anhören" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Langsam anhören" })).toBeInTheDocument();
  });

  it("zeigt ohne Stimme den deutschen Prompt statt der Knöpfe", () => {
    mockSpeech(false);
    render(<AudioPrompt text="ско́лько тебе́ лет" promptDe="Wie alt bist du?" />);
    expect(screen.getByText("Wie alt bist du?")).toBeInTheDocument();
    expect(screen.queryByRole("button")).toBeNull();
  });

  it("spielt bei eingeschalteter Automatik einmal von allein ab", () => {
    const say = mockSpeech(true, true);
    render(<AudioPrompt text="дом" promptDe="Haus" />);
    expect(say).toHaveBeenCalledWith("дом", { slow: false });
  });

  it("spielt bei ausgeschalteter Automatik nichts von allein ab", () => {
    const say = mockSpeech(true, false);
    render(<AudioPrompt text="дом" promptDe="Haus" />);
    expect(say).not.toHaveBeenCalled();
  });
});
```

In `frontend/src/course/exercises.test.tsx` ergänzen:

```tsx
describe("BuildSentenceExercise mit Ton", () => {
  it("zeigt statt des deutschen Prompts den Abspielknopf", () => {
    vi.spyOn(context, "useSpeech").mockReturnValue({
      available: true, autoplay: false, setAutoplay: vi.fn(), say: vi.fn(),
    });
    render(
      <BuildSentenceExercise
        exercise={{ ...build, audio_prompt: true, audio_text: "как вас зовут" }}
        onSubmit={vi.fn()}
      />,
    );
    expect(screen.queryByText("Wie heißen Sie?")).toBeNull();
    expect(screen.getByRole("button", { name: "Anhören" })).toBeInTheDocument();
  });

  it("fällt ohne Stimme auf den deutschen Prompt zurück", () => {
    vi.spyOn(context, "useSpeech").mockReturnValue({
      available: false, autoplay: true, setAutoplay: vi.fn(), say: vi.fn(),
    });
    render(
      <BuildSentenceExercise
        exercise={{ ...build, audio_prompt: true, audio_text: "как вас зовут" }}
        onSubmit={vi.fn()}
      />,
    );
    expect(screen.getByText("Wie heißen Sie?")).toBeInTheDocument();
  });
});
```

Die bestehenden Fixtures `build` und `choose` in dieser Datei um `audio_prompt: false` erweitern.

- [ ] **Step 2: Run tests to verify they fail**

Run: `npm test --prefix frontend -- AudioPrompt exercises`
Expected: FAIL — `AudioPrompt` existiert nicht.

- [ ] **Step 3: Implement**

`frontend/src/course/AudioPrompt.tsx`:

```tsx
import { useEffect, useRef } from "react";

import SpeakerButton from "../audio/SpeakerButton";
import { useSpeech } from "../audio/SpeechContext";

export default function AudioPrompt({
  text,
  promptDe,
}: {
  text: string;
  promptDe: string;
}) {
  const { available, autoplay, say } = useSpeech();
  const played = useRef(false);

  useEffect(() => {
    // Einmal beim Betreten vorspielen. Browser blockieren das vor der ersten
    // Nutzergeste — dafuer gibt es den Knopf.
    if (available && autoplay && !played.current) {
      played.current = true;
      say(text, { slow: false });
    }
  }, [available, autoplay, say, text]);

  if (!available) return <p className="text-lg">{promptDe}</p>;

  return (
    <div className="flex items-center gap-2">
      <SpeakerButton text={text} />
      <SpeakerButton text={text} slow label="Langsam anhören" />
      <span className="text-slate-500">Hör zu.</span>
    </div>
  );
}
```

In `courseTypes.ts` bei `BuildSentenceExercise` und `ChooseFormExercise` je `audio_prompt: boolean;` und `audio_text?: string;` ergänzen.

In beiden Komponenten die Prompt-Zeile ersetzen:

```tsx
      {exercise.audio_prompt && exercise.audio_text ? (
        <AudioPrompt text={exercise.audio_text} promptDe={exercise.prompt_de} />
      ) : (
        <p className="text-lg">{exercise.prompt_de}</p>
      )}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `npm test --prefix frontend`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/course/ frontend/src/courseTypes.ts
git commit -m "feat(course): play the sentence instead of showing the German prompt"
```

---

### Task 10: `ListenMeaningExercise` im Frontend

**Files:**
- Create: `frontend/src/course/ListenMeaningExercise.tsx`
- Modify: `frontend/src/courseTypes.ts`, `frontend/src/course/ExerciseRunner.tsx`
- Test: `frontend/src/course/ListenMeaningExercise.test.tsx`

**Interfaces:**
- Consumes: `AudioPrompt` (Task 9), `RussianText`
- Produces: Typ `ListenMeaningExercise { id; type: "listen_meaning"; prompt_de; audio_text; sentence: Word[]; options_de: string[] }`, Einreichung `{ option_index: number }`

- [ ] **Step 1: Write the failing test**

```tsx
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import * as context from "../audio/SpeechContext";
import ListenMeaningExercise from "./ListenMeaningExercise";

const exercise = {
  id: "25-7",
  type: "listen_meaning" as const,
  prompt_de: "Hör zu. Was wird gesagt?",
  audio_text: "я живу́ в Берли́не",
  sentence: [
    { text: "я", translit: "ja" },
    { text: "живу́", translit: "živú" },
  ],
  options_de: ["Ich fahre nach Berlin.", "Ich wohne in Berlin.", "Er wohnt in Berlin."],
};

const mockSpeech = (available: boolean) =>
  vi.spyOn(context, "useSpeech").mockReturnValue({
    available,
    autoplay: false,
    setAutoplay: vi.fn(),
    say: vi.fn(),
  });

describe("ListenMeaningExercise", () => {
  it("schickt den angeklickten Anzeige-Index", () => {
    mockSpeech(true);
    const onSubmit = vi.fn();
    render(<ListenMeaningExercise exercise={exercise} onSubmit={onSubmit} />);
    fireEvent.click(screen.getByRole("button", { name: "Ich wohne in Berlin." }));
    expect(onSubmit).toHaveBeenCalledWith({ option_index: 1 });
  });

  it("verrät den Satz nicht, solange eine Stimme da ist", () => {
    mockSpeech(true);
    render(<ListenMeaningExercise exercise={exercise} onSubmit={vi.fn()} />);
    expect(screen.queryByText("живу́")).toBeNull();
  });

  it("zeigt ohne Stimme den Satz als Text und bleibt lösbar", () => {
    mockSpeech(false);
    const onSubmit = vi.fn();
    render(<ListenMeaningExercise exercise={exercise} onSubmit={onSubmit} />);
    expect(screen.getByText("живу́")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Er wohnt in Berlin." }));
    expect(onSubmit).toHaveBeenCalledWith({ option_index: 2 });
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test --prefix frontend -- ListenMeaning`
Expected: FAIL — Modul existiert nicht.

- [ ] **Step 3: Implement**

```tsx
import { useSpeech } from "../audio/SpeechContext";
import type { ListenMeaningExercise as Model, Submission } from "../courseTypes";
import AudioPrompt from "./AudioPrompt";
import RussianText from "./RussianText";

export default function ListenMeaningExercise({
  exercise,
  disabled = false,
  onSubmit,
}: {
  exercise: Model;
  disabled?: boolean;
  onSubmit: (submission: Submission) => void;
}) {
  const { available } = useSpeech();

  return (
    <div className="space-y-4">
      <AudioPrompt text={exercise.audio_text} promptDe={exercise.prompt_de} />
      {available ? null : (
        <div className="flex flex-wrap items-end gap-3 text-xl">
          {exercise.sentence.map((word, position) => (
            <RussianText key={`word-${position}`} word={word} />
          ))}
        </div>
      )}
      <div className="flex flex-col gap-2">
        {exercise.options_de.map((option, index) => (
          <button
            key={option}
            type="button"
            disabled={disabled}
            onClick={() => onSubmit({ option_index: index })}
            className="rounded-xl border-2 border-slate-300 bg-white px-4 py-2 text-left text-lg hover:border-sky-400 disabled:opacity-60"
          >
            {option}
          </button>
        ))}
      </div>
    </div>
  );
}
```

In `courseTypes.ts` den Typ ergänzen und in die `Exercise`-Union aufnehmen. In `ExerciseRunner.tsx` den Fall ergänzen:

```tsx
    case "listen_meaning":
      return <ListenMeaningExercise exercise={exercise} {...props} />;
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npm test --prefix frontend`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/course/ frontend/src/courseTypes.ts
git commit -m "feat(course): add the listen-and-choose-meaning exercise"
```

---

### Task 11: Hörzeile in der Auflösung

`UnitView` zeigt die Lösung bisher **nur bei falscher Antwort**. Für Hörtraining will man den Satz gerade nach einer richtigen Antwort hören. Bei `match_pairs` gibt es keinen Satz, sondern eine Wortliste — dort bekommt jedes Wort einen eigenen Lautsprecher.

**Files:**
- Modify: `frontend/src/views/UnitView.tsx:95-115`, `frontend/src/courseTypes.ts` (`AnswerResult`)
- Modify: `backend/app/course/service.py` (`AnswerOutcome`), `backend/app/api/schemas.py` (`AnswerResponse`), `backend/app/course/checker.py`
- Test: `frontend/src/views/UnitView.test.tsx`, `backend/tests/test_course_service.py`

**Interfaces:**
- Produces: `CheckResult.solution_audio: list[str]` — die zu sprechenden Einzelteile der Lösung (bei Satzaufgaben genau ein Eintrag, bei `match_pairs` einer je Wort). Wandert unverändert durch `AnswerOutcome` und `AnswerResponse` in `AnswerResult.solution_audio: string[]`.

- [ ] **Step 1: Write the failing tests**

`backend/tests/test_course_checker.py`:

```python
def test_satzaufgabe_liefert_einen_audio_teil(course):
    exercise = BuildSentenceExercise(
        id="22-4", prompt_de="…",
        solution=[("skolko", "base"), ("ty", "dat")], distractors=[],
    )
    result = check_answer(course, exercise, {"tile_indices": []})
    assert result.solution_audio == ["ско́лько тебе́"]


def test_match_pairs_liefert_ein_audio_je_wort(course):
    exercise = MatchPairsExercise(
        id="1-1", prompt_de="…", pairs=[("bu_r", "base"), ("bu_n", "base")]
    )
    result = check_answer(course, exercise, {"pairs": []})
    assert result.solution_audio == ["ры́ба", "но́мер"]
```

`frontend/src/views/UnitView.test.tsx` — nach einer **richtigen** Antwort muss ein Lautsprecher erscheinen:

```tsx
it("bietet die Lösung auch nach einer richtigen Antwort zum Anhören an", async () => {
  // getUnit/submitAnswer wie in den bestehenden Tests dieser Datei mocken,
  // submitAnswer liefert { correct: true, solution_text: "дом",
  //   solution_audio: ["дом"], explanation_de: "", ... }
  // useSpeech mit available: true mocken.
  render(<UnitView />, { wrapper });
  // ... Aufgabe lösen ...
  expect(await screen.findByRole("button", { name: "Anhören" })).toBeInTheDocument();
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `backend/.venv/bin/python -m pytest tests/test_course_checker.py -v` und `npm test --prefix frontend -- UnitView`
Expected: FAIL — `solution_audio` existiert nicht.

- [ ] **Step 3: Implement**

In `checker.py` `CheckResult` um `solution_audio: list[str]` erweitern. In `_render` bleibt es beim Bisherigen; zusätzlich in jedem `_check_*`:

- `_check_build_sentence`: `solution_audio=[spoken_text(course, list(exercise.solution))]`
- `_check_choose_form`: `solution_audio=[spoken_text(course, [exercise.answer])]`
- `_check_dialog_reply`: `solution_audio=[spoken_text(course, list(correct_option.tokens))]`
- `_check_listen_meaning`: `solution_audio=[spoken_text(course, list(exercise.sentence))]`
- `_check_match_pairs`: `solution_audio=[spoken_text(course, [pair]) for pair in exercise.pairs]`

`spoken_text` aus `app.course.presenter` importieren.

In `service.py` `AnswerOutcome` um `solution_audio: list[str]` erweitern und aus `result` durchreichen; in `schemas.py` `AnswerResponse` um `solution_audio: list[str] = []`; in `routes.py` mitgeben.

In `courseTypes.ts` `AnswerResult` um `solution_audio: string[];` erweitern.

In `UnitView.tsx` den Rückmeldeblock ergänzen — die „Richtig ist"-Zeile bleibt wie sie ist, darunter kommt in **beiden** Fällen:

```tsx
          {result.solution_audio.length > 0 ? (
            <div className="flex flex-wrap items-center gap-2">
              {result.solution_audio.map((part) => (
                <span key={part} className="flex items-center gap-1">
                  <span lang="ru">{part}</span>
                  <SpeakerButton text={part} />
                </span>
              ))}
            </div>
          ) : null}
```

`SpeakerButton` rendert von sich aus nichts, wenn keine Stimme da ist — es braucht also keine zusätzliche Bedingung.

- [ ] **Step 4: Run tests to verify they pass**

Run: `backend/.venv/bin/python -m pytest -v` und `npm test --prefix frontend`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app backend/tests frontend/src
git commit -m "feat(course): offer the solution for listening after every answer"
```

---

### Task 12: Lautsprecher in der Wiederholungs-Auflösung

**Files:**
- Modify: `frontend/src/views/ReviewView.tsx`
- Test: `frontend/src/views/ReviewView.test.tsx`

**Interfaces:**
- Consumes: `SpeakerButton` (Task 7); `ReviewResult.results[].text` liegt bereits vor

- [ ] **Step 1: Write the failing test**

```tsx
it("lässt jede Form der Auflösung anhören", async () => {
  // useSpeech mit available: true mocken, gradeReview liefert
  // results: [{ ref: "god:gen.pl", correct: true, gloss_de: "Jahr", text: "лет" }]
  render(<ReviewView />, { wrapper });
  // ... Runde abschicken ...
  expect(await screen.findAllByRole("button", { name: "Anhören" })).toHaveLength(1);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test --prefix frontend -- ReviewView`
Expected: FAIL — kein Knopf „Anhören".

- [ ] **Step 3: Implement**

In der Ergebnisliste von `ReviewView.tsx` je Zeile `<SpeakerButton text={item.text} />` ergänzen.

- [ ] **Step 4: Run test to verify it passes**

Run: `npm test --prefix frontend`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/views/
git commit -m "feat(review): let every reviewed form be heard in the results"
```

---

### Task 13: Hinweis im Profil bei fehlender Stimme

**Files:**
- Modify: `frontend/src/ProfileView.tsx`
- Test: `frontend/src/ProfileView.test.tsx`

- [ ] **Step 1: Write the failing test**

```tsx
it("erklärt, was zu tun ist, wenn keine russische Stimme da ist", async () => {
  vi.spyOn(context, "useSpeech").mockReturnValue({
    available: false, autoplay: true, setAutoplay: vi.fn(), say: vi.fn(),
  });
  render(<ProfileView />, { wrapper });
  expect(await screen.findByText(/keine russische Stimme/i)).toBeInTheDocument();
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test --prefix frontend -- ProfileView`
Expected: FAIL.

- [ ] **Step 3: Implement**

Einen Abschnitt ergänzen, der nur bei `available === false` erscheint:

```tsx
      {available === false ? (
        <section className="rounded-2xl border-2 border-amber-200 bg-amber-50 p-4">
          <h2 className="text-lg font-semibold">Kein Ton</h2>
          <p className="mt-1">
            Dein Browser findet keine russische Stimme. Hör-Aufgaben werden deshalb als
            Textaufgaben angezeigt. Unter Windows installierst du eine Stimme über
            Einstellungen → Zeit und Sprache → Sprache, unter Linux über das Paket
            <code className="mx-1">speech-dispatcher</code>
            mit russischer Stimme.
          </p>
        </section>
      ) : null}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npm test --prefix frontend`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/ProfileView.tsx frontend/src/ProfileView.test.tsx
git commit -m "feat(profile): explain how to install a Russian voice when none is found"
```

---

### Task 14: `speak_as` für die Buchstaben (Einheiten 1–4)

**Files:**
- Modify: `content/ru/lexicon.json`
- Test: `backend/tests/test_real_content.py`

- [ ] **Step 1: Write the failing test**

```python
def test_alle_buchstaben_haben_ein_beispielwort_zum_anhoeren(real_course):
    ohne = [
        lexeme.id
        for lexeme in real_course.lexemes.values()
        if lexeme.pos == "letter" and not lexeme.forms["base"].speak_as
    ]
    assert ohne == [], f"Buchstaben ohne speak_as: {ohne}"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `backend/.venv/bin/python -m pytest tests/test_real_content.py -v`
Expected: FAIL mit einer Liste aller Buchstaben-Lexeme.

- [ ] **Step 3: Implement**

Jedem Lexem mit `"pos": "letter"` in `content/ru/lexicon.json` ein `speak_as` an seiner `base`-Form geben: ein **kurzes, bereits im Kurs vorkommendes oder alltägliches Wort**, in dem der Laut deutlich hörbar ist, mit Betonungszeichen. Beispiele:

```
bu_r  → "ры́ба"      bu_n  → "но́мер"     bu_v  → "вода́"
bu_s  → "суп"        bu_u  → "у́тро"      bu_h  → "хорошо́"
bu_zh → "журна́л"    bu_ts → "центр"     bu_ch → "чай"
bu_sh → "шко́ла"     bu_shch → "борщ"
```

Für die übrigen Buchstaben nach demselben Muster verfahren. Der Laut muss im gewählten Wort **betont oder zumindest unreduziert** vorkommen — sonst hört man ihn nicht (`о` in `молоко́` klingt wie [a], taugt also nicht als Beispiel für `о`).

- [ ] **Step 4: Run tests to verify they pass**

Run: `backend/.venv/bin/python -m pytest -v` und `make validate`
Expected: PASS, `make validate` ohne Befund.

- [ ] **Step 5: Commit**

```bash
git add content/ru/lexicon.json backend/tests/test_real_content.py
git commit -m "content: give every letter an example word to hear its sound in"
```

---

### Task 15: Hör-Aufgaben in den Einheiten 5–14

**Files:**
- Modify: `content/ru/units/005.json` … `014.json`
- Test: `backend/tests/test_real_content.py`

- [ ] **Step 1: Write the failing test**

```python
def test_jede_sprachliche_einheit_hat_mindestens_eine_hoeraufgabe(real_course):
    ohne = [
        unit.id
        for unit in real_course.ordered_units()
        if unit.stage > 0
        and not any(
            getattr(exercise, "audio_prompt", False)
            or exercise.type == "listen_meaning"
            for exercise in unit.exercises
        )
    ]
    assert ohne == [], f"Einheiten ohne Hör-Aufgabe: {ohne}"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `backend/.venv/bin/python -m pytest tests/test_real_content.py -v`
Expected: FAIL — Einheiten 5–24 fehlen alle.

- [ ] **Step 3: Implement**

In jeder Einheit 5–14 **eine bestehende** `build_sentence`- oder `choose_form`-Aufgabe um `"audio_prompt": true` erweitern. Auswahlregel: die Aufgabe, deren Satz den Grammatik-Fokus der Einheit am deutlichsten trägt.

Wo es inhaltlich trägt, zusätzlich **eine** `listen_meaning`-Aufgabe anhängen. Deren `options_de` müssen Beinahe-Treffer sein, die sich in genau einer Form oder einem Wort unterscheiden — und alle vorkommenden Lexeme müssen in dieser oder einer früheren Einheit eingeführt sein, sonst schlägt die Vokabelreihenfolge-Prüfung an. Die `id` folgt dem Schema der Einheit (`"12-8"` als achte Aufgabe der zwölften Einheit).

- [ ] **Step 4: Verify**

Run: `make validate` und `backend/.venv/bin/python -m pytest tests/test_real_content.py -v`
Expected: `make validate` ohne Befund; der Test meldet jetzt nur noch die Einheiten 15–24.

- [ ] **Step 5: Commit**

```bash
git add content/ru/units/
git commit -m "content: add listening exercises to units 5-14"
```

---

### Task 16: Hör-Aufgaben in den Einheiten 15–24

**Files:**
- Modify: `content/ru/units/015.json` … `024.json`

- [ ] **Step 1: Run the test from Task 15 to see what is missing**

Run: `backend/.venv/bin/python -m pytest tests/test_real_content.py -v`
Expected: FAIL mit den Einheiten 15–24.

- [ ] **Step 2: Implement**

Genau wie Task 15, für die Einheiten 15–24.

- [ ] **Step 3: Verify**

Run: `make validate` und `backend/.venv/bin/python -m pytest -v`
Expected: alles grün, `test_jede_sprachliche_einheit_hat_mindestens_eine_hoeraufgabe` besteht.

- [ ] **Step 4: Commit**

```bash
git add content/ru/units/
git commit -m "content: add listening exercises to units 15-24"
```

---

### Task 17: e2e-Lauf mit gefälschter Sprachausgabe

**Files:**
- Create: `frontend/e2e/hoeren.spec.ts`
- Test: derselbe

**Interfaces:**
- Consumes: den bestehenden Aufbau aus `frontend/e2e/kurs.spec.ts` (eigene Ports, frische Datenbank je Lauf)

- [ ] **Step 1: Write the failing test**

```ts
import { expect, test } from "@playwright/test";

/** Ersetzt die Sprachausgabe durch eine Attrappe, die mitschreibt statt zu sprechen. */
const stubVoices = (langs: string[]) => `
  window.__spoken = [];
  window.speechSynthesis = {
    getVoices: () => ${JSON.stringify(langs)}.map((lang) => ({ lang, name: lang })),
    addEventListener: () => {},
    removeEventListener: () => {},
    cancel: () => {},
    speak: (utterance) => window.__spoken.push(utterance.text),
  };
  window.SpeechSynthesisUtterance = class {
    constructor(text) { this.text = text; this.rate = 1; this.lang = ""; this.voice = null; }
  };
`;

test("spricht den Satz einer Hör-Aufgabe", async ({ page }) => {
  await page.addInitScript(stubVoices(["ru-RU"]));
  await page.goto("/kurs/22");
  await page.getByRole("button", { name: "Los geht's" }).click();
  await page.getByRole("button", { name: "Anhören" }).first().click();
  const spoken = await page.evaluate(() => (window as any).__spoken as string[]);
  expect(spoken.join(" ")).not.toContain("́");
  expect(spoken.length).toBeGreaterThan(0);
});

test("bleibt ohne russische Stimme lösbar", async ({ page }) => {
  await page.addInitScript(stubVoices(["de-DE"]));
  await page.goto("/kurs/22");
  await page.getByRole("button", { name: "Los geht's" }).click();
  await expect(page.getByRole("button", { name: "Anhören" })).toHaveCount(0);
  // Der deutsche Prompt der ersten Aufgabe ist sichtbar, die Einheit ist bedienbar.
  await expect(page.locator("text=Aufgabe 1 von")).toBeVisible();
});
```

Die konkrete Einheit und der erwartete Prompt sind an den Stand nach Task 15/16 anzupassen — es muss eine Einheit sein, deren **erste** Aufgabe eine Hör-Aufgabe ist, sonst greift der Selektor nicht.

- [ ] **Step 2: Run test to verify it fails**

Run: `make test-e2e`
Expected: FAIL, solange die Spec-Datei fehlt bzw. die Aufgaben noch keinen Ton haben.

- [ ] **Step 3: Implement**

Datei anlegen wie oben; falls nötig in Task 15 eine Einheit so anpassen, dass ihre erste Aufgabe eine Hör-Aufgabe ist.

- [ ] **Step 4: Run the full suite**

Run: `make test && make test-e2e && make validate`
Expected: alles grün.

- [ ] **Step 5: Commit**

```bash
git add frontend/e2e/
git commit -m "test(e2e): cover listening exercises with and without a Russian voice"
```

---

## Selbstprüfung des Plans

**Spec-Abdeckung**

| Spec-Abschnitt | Task |
|---|---|
| 3.1 `audio_prompt` | 2 |
| 3.2 `listen_meaning` | 3, 10 |
| 3.3 `speak_as` | 1, 14 |
| 3.4 Validator-Regeln | 1, 2, 3 |
| 4.1 Presenter | 2, 3 |
| 4.2 Checker | 3, 11 |
| 4.3 Textrückfall | 9, 10 (Tests), 17 |
| 4.4 Profil | 4, 8 |
| 5.1 `speech.ts` | 5 |
| 5.2 `SpeechContext` | 6 |
| 5.3 Lautsprecher auf Satzebene | 7, 11, 12 |
| 5.4 Kopfzeilen-Schalter, Autoplay | 8, 9 |
| 6 Inhalte | 14, 15, 16 |
| 7 Tests | in jeder Task, e2e in 17 |

**Abweichungen von der Spec, bewusst und begründet**

1. **Kein Lautsprecher in `VocabView`.** Die Spec nennt die Vokabelliste als vierten Ort. `VocabView.tsx` ist jedoch toter Code aus Phase 1 — nirgends importiert, keine Route, fragt getippte englische Übersetzungen ab. Ein Lautsprecher dort wäre unerreichbar. Eine neue Vokabelliste anzulegen wäre Scope-Ausweitung. Ersatz: die Auflösung liefert bei `match_pairs` einen Lautsprecher **je Wort** (Task 11), womit Einzelwörter hörbar bleiben und die Buchstaben-Einheiten 1–4 versorgt sind.
2. **Die Auflösung erscheint jetzt auch bei richtiger Antwort** (Task 11). Bisher zeigt `UnitView` die Lösung nur bei Fehlern; ein Lautsprecher „an der aufgelösten Lösung" wäre sonst nur nach Fehlern erreichbar — genau verkehrt für Hörtraining.
3. **`solution_audio` als eigenes Feld** statt den Client `solution_text` sprechen zu lassen: `solution_text` enthält bei `match_pairs` alle Wörter in einer Zeichenkette und berücksichtigt `speak_as` nicht.

**Typkonsistenz geprüft:** `speak_as` (Task 1) → `spoken_text` (Task 2) → `audio_text` (Task 2, 3) → `AudioPrompt` (Task 9); `useSpeech().say` (Task 6) → `SpeakerButton`, `AutoplayToggle`, `AudioPrompt` (Tasks 7–9); `solution_audio` durchgängig `list[str]` / `string[]` (Task 11).
