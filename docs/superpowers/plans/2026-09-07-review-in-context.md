# Fehler-Nachlauf und Wiederholung im Kontext — Implementierungsplan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Falsch beantwortete Aufgaben kommen bis zur richtigen Antwort wieder, und die Wiederholung fragt fällige Wortformen in echten Kursaufgaben ab statt in einer Zuordnung.

**Architecture:** Ein Index bildet jede Wortform auf die Kursaufgaben ab, die sie im Kontext trainieren. Die Wiederholungsrunde wird zu einer Liste von Einträgen — echte Aufgaben, plus höchstens eine Zuordnung für alles ohne Kontext-Aufgabe. Der Fehler-Nachlauf ist reine Frontend-Logik: eine Warteschlange statt eines Zählers.

**Tech Stack:** Python 3.11 / FastAPI / SQLite / pytest; React 18 / TypeScript / Vitest; Playwright.

**Spec:** `docs/superpowers/specs/2026-09-07-speaker-review-in-context-design.md`

## Global Constraints

- Alle Nutzertexte auf **Deutsch**.
- `POST /api/review/exercise` ruft **niemals** `bump_progress` oder `record_attempt` auf — eine Wiederholung darf keine abgeschlossene Einheit wieder aufreißen.
- Kontext-Aufgaben nur aus Einheiten, in denen der Lernende schon gearbeitet hat.
- Höchstens **ein** Zuordnungs-Eintrag je Runde, und nie mit weniger als **zwei** Paaren.
- Der Fehler-Nachlauf ist **rein im Frontend**; das Backend erfasst Richtigkeit bereits.
- `make test` (enthält `tsc`, pytest, tts-Tests, Vitest) und `make test-e2e` headless — **nie** `make test-e2e-show`.

## Dateiübersicht

**Neu**

| Datei | Verantwortung |
|---|---|
| `backend/app/course/review_index.py` | Wortform → Kursaufgaben, die sie im Kontext trainieren |
| `backend/tests/test_review_index.py` | genau vor weit, Fortschrittsfilter, Los |
| `frontend/src/views/ReviewView.test.tsx` | erweitert um die neue Eintragsart |

**Geändert**

| Datei | Änderung |
|---|---|
| `backend/app/course/review.py` | Runde als Liste von Einträgen |
| `backend/app/course/service.py` | `submit_review_exercise` ohne Einheiten-Buchführung |
| `backend/app/api/routes.py`, `schemas.py` | `POST /api/review/exercise` |
| `backend/app/dependencies.py` | `get_review_index()` |
| `backend/tests/test_course_review.py`, `test_routes.py`, `test_real_content.py` | neue Zusagen |
| `frontend/src/views/UnitView.tsx` | Warteschlange statt Zähler |
| `frontend/src/views/ReviewView.tsx` | läuft die Einträge durch |
| `frontend/src/courseTypes.ts`, `courseApi.ts` | neue Typen und Aufruf |
| `frontend/e2e/kurs.spec.ts` | Fehler-Nachlauf |

---

### Task 1: Der Index

**Files:**
- Create: `backend/app/course/review_index.py`, `backend/tests/test_review_index.py`
- Modify: `backend/app/dependencies.py`

**Interfaces:**
- Produces:
  - `ReviewIndex` mit `exact: dict[TokenRef, list[tuple[int, str]]]` und `broad: dict[...]`
  - `build_index(course: Course) -> ReviewIndex`
  - `ReviewIndex.pick(ref, *, allowed_units: set[int], seed: str) -> tuple[int, str] | None`
  - `dependencies.get_review_index() -> ReviewIndex`

- [ ] **Step 1: Write the failing test**

`backend/tests/test_review_index.py`:

```python
import copy

from app.content.loader import load_course
from app.course.review_index import build_index
from tests.content_factory import MINIMAL_UNIT, write_course


def _course(tmp_path, units=None):
    return load_course(write_course(tmp_path, units=units))


def test_choose_form_landet_unter_genau(tmp_path):
    index = build_index(_course(tmp_path))
    # 1-2 ist die choose_form mit answer ("delat", "prs.1sg")
    assert (1, "1-2") in index.exact[("delat", "prs.1sg")]


def test_build_sentence_landet_unter_weit(tmp_path):
    index = build_index(_course(tmp_path))
    # 1-1 ist die build_sentence mit ("ja", "nom") in der Loesung
    assert (1, "1-1") in index.broad[("ja", "nom")]


def test_pick_bevorzugt_die_genaue_aufgabe(tmp_path):
    index = build_index(_course(tmp_path))
    treffer = index.pick(("delat", "prs.1sg"), allowed_units={1}, seed="x")
    assert treffer == (1, "1-2")


def test_pick_nimmt_weit_wenn_es_nichts_genaues_gibt(tmp_path):
    index = build_index(_course(tmp_path))
    assert index.pick(("ja", "nom"), allowed_units={1}, seed="x") == (1, "1-1")


def test_pick_meidet_einheiten_ohne_fortschritt(tmp_path):
    index = build_index(_course(tmp_path))
    assert index.pick(("delat", "prs.1sg"), allowed_units=set(), seed="x") is None


def test_pick_liefert_none_fuer_unbekannte_form(tmp_path):
    index = build_index(_course(tmp_path))
    assert index.pick(("gibtesnicht", "nom"), allowed_units={1}, seed="x") is None


def test_pick_streut_ueber_mehrere_kandidaten(tmp_path):
    # Zwei choose_form-Aufgaben auf dieselbe Form: die Wahl darf nicht
    # immer auf dieselbe fallen, sonst sieht man ewig denselben Satz.
    unit = copy.deepcopy(MINIMAL_UNIT)
    zweite = copy.deepcopy(unit["exercises"][1])
    zweite["id"] = "1-9"
    unit["exercises"] = unit["exercises"] + [zweite]
    index = build_index(_course(tmp_path, units=[unit]))

    gewaehlt = {
        index.pick(("delat", "prs.1sg"), allowed_units={1}, seed=f"tag-{tag}")
        for tag in range(12)
    }
    assert len(gewaehlt) == 2


def test_pick_ist_innerhalb_eines_tages_stabil(tmp_path):
    index = build_index(_course(tmp_path))
    a = index.pick(("delat", "prs.1sg"), allowed_units={1}, seed="2026-09-07")
    b = index.pick(("delat", "prs.1sg"), allowed_units={1}, seed="2026-09-07")
    assert a == b
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && .venv/bin/python -m pytest tests/test_review_index.py -q -p no:cacheprovider`
Expected: FAIL — `app.course.review_index` existiert nicht.

- [ ] **Step 3: Write the implementation**

`backend/app/course/review_index.py`:

```python
from dataclasses import dataclass, field

from app.content.models import BuildSentenceExercise, ChooseFormExercise, Course, TokenRef
from app.course.shuffle import shuffled_order

Location = tuple[int, str]
"""(unit_id, exercise_id) — so viel braucht der Client, um die Aufgabe zu benennen."""


@dataclass(frozen=True)
class ReviewIndex:
    """Welche Aufgaben trainieren eine Wortform im Satz?

    Zwei Abbildungen, weil sie unterschiedlich gut treffen: bei `choose_form`
    *ist* die Form die Loesung, bei `build_sentence` kommt sie unter anderen vor.
    """

    exact: dict[TokenRef, list[Location]] = field(default_factory=dict)
    broad: dict[TokenRef, list[Location]] = field(default_factory=dict)

    def pick(self, ref: TokenRef, *, allowed_units: set[int], seed: str) -> Location | None:
        for table in (self.exact, self.broad):
            candidates = [
                location for location in table.get(ref, []) if location[0] in allowed_units
            ]
            if not candidates:
                continue
            # Los statt „immer die erste": sonst sieht man ewig denselben Satz.
            order = shuffled_order(f"{seed}:{ref[0]}:{ref[1]}", len(candidates))
            return candidates[order[0]]
        return None


def build_index(course: Course) -> ReviewIndex:
    exact: dict[TokenRef, list[Location]] = {}
    broad: dict[TokenRef, list[Location]] = {}
    for unit in course.ordered_units():
        for exercise in unit.exercises:
            where = (unit.id, exercise.id)
            if isinstance(exercise, ChooseFormExercise):
                exact.setdefault(exercise.answer, []).append(where)
            elif isinstance(exercise, BuildSentenceExercise):
                for ref in exercise.solution:
                    broad.setdefault(ref, []).append(where)
    return ReviewIndex(exact=exact, broad=broad)
```

In `backend/app/dependencies.py`:

```python
from app.course.review_index import ReviewIndex, build_index


@lru_cache(maxsize=1)
def _review_index() -> ReviewIndex:
    return build_index(_load_course())


def get_review_index() -> ReviewIndex:
    return _review_index()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && .venv/bin/python -m pytest -q -p no:cacheprovider`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/course/review_index.py backend/app/dependencies.py backend/tests/test_review_index.py
git commit -m "feat(review): index which exercises train each word form in context"
```

---

### Task 2: Die Runde als Liste von Einträgen

**Files:**
- Modify: `backend/app/course/review.py`, `backend/tests/test_course_review.py`

**Interfaces:**
- Consumes: `ReviewIndex.pick` (Task 1)
- Produces: `build_review_round(conn, course, index, *, today, size=5) -> {"items": [...]}` mit Einträgen `{"kind": "exercise", "unit_id", "exercise_id", "ref", **present_exercise}` und höchstens einem `{"kind": "pairs", "left", "right"}`
- `grade_review_round` bleibt unverändert und bedient den Zuordnungs-Eintrag.

- [ ] **Step 1: Write the failing test**

An `backend/tests/test_course_review.py` anhängen:

```python
def test_runde_nutzt_eine_kontext_aufgabe_wenn_es_eine_gibt(conn, tmp_path):
    course = load_course(write_course(tmp_path))
    index = build_index(course)
    progress_repo.bump_progress(conn, unit_id=1, correct=True)
    schedule_form(conn, ("delat", "prs.1sg"), correct=False, today="2026-01-01")

    runde = build_review_round(conn, course, index, today="2026-01-02")
    aufgaben = [item for item in runde["items"] if item["kind"] == "exercise"]
    assert aufgaben, "die faellige Form hat eine choose_form-Aufgabe"
    assert aufgaben[0]["unit_id"] == 1
    assert aufgaben[0]["ref"] == "delat:prs.1sg"
    assert aufgaben[0]["type"] == "choose_form"


def test_formen_ohne_kontext_aufgabe_kommen_als_zuordnung(conn, tmp_path):
    lexicon = copy.deepcopy(MINIMAL_LEXICON)
    lexicon["lexemes"].append(
        {
            "id": "bu_r",
            "lemma": "Р р",
            "pos": "letter",
            "gloss_de": "gerolltes r",
            "forms": {"base": {"text": "Р р", "translit": "r"}},
        }
    )
    lexicon["lexemes"].append(
        {
            "id": "bu_n",
            "lemma": "Н н",
            "pos": "letter",
            "gloss_de": "n",
            "forms": {"base": {"text": "Н н", "translit": "n"}},
        }
    )
    course = load_course(write_course(tmp_path, lexicon=lexicon))
    index = build_index(course)
    progress_repo.bump_progress(conn, unit_id=1, correct=True)
    for ref in (("bu_r", "base"), ("bu_n", "base")):
        schedule_form(conn, ref, correct=False, today="2026-01-01")

    runde = build_review_round(conn, course, index, today="2026-01-02")
    zuordnungen = [item for item in runde["items"] if item["kind"] == "pairs"]
    assert len(zuordnungen) == 1, "hoechstens eine Zuordnung je Runde"
    assert len(zuordnungen[0]["left"]) == 2


def test_ohne_faellige_formen_ist_die_runde_leer(conn, tmp_path):
    course = load_course(write_course(tmp_path))
    assert build_review_round(conn, course, build_index(course), today="2026-01-02")["items"] == []


def test_eine_einzelne_form_ohne_kontext_wird_aufgefuellt(conn, tmp_path):
    # Eine Zuordnung mit einem Paar ist keine Aufgabe. Ohne Auffuellen fiele
    # die Form Runde fuer Runde durch und wuerde nie wiederholt.
    lexicon = copy.deepcopy(MINIMAL_LEXICON)
    lexicon["lexemes"].append(
        {
            "id": "bu_r",
            "lemma": "Р р",
            "pos": "letter",
            "gloss_de": "gerolltes r",
            "forms": {"base": {"text": "Р р", "translit": "r"}},
        }
    )
    course = load_course(write_course(tmp_path, lexicon=lexicon))
    index = build_index(course)
    progress_repo.bump_progress(conn, unit_id=1, correct=True)
    schedule_form(conn, ("bu_r", "base"), correct=False, today="2026-01-01")
    schedule_form(conn, ("delat", "prs.1sg"), correct=False, today="2026-01-01")

    runde = build_review_round(conn, course, index, today="2026-01-02")
    zuordnungen = [item for item in runde["items"] if item["kind"] == "pairs"]
    assert len(zuordnungen) == 1
    assert len(zuordnungen[0]["left"]) == 2, "die einzelne Form bekommt Gesellschaft"


def test_aufgaben_aus_unbearbeiteten_einheiten_kommen_nicht(conn, tmp_path):
    course = load_course(write_course(tmp_path))
    index = build_index(course)
    # kein bump_progress: die Einheit wurde nie angefasst
    schedule_form(conn, ("delat", "prs.1sg"), correct=False, today="2026-01-01")

    runde = build_review_round(conn, course, index, today="2026-01-02")
    assert [item for item in runde["items"] if item["kind"] == "exercise"] == []
```

Die Datei braucht dafür `import copy`, `from app.course.review_index import build_index`,
`from app.course.service import schedule_form`, `from app.repositories import progress_repo` und
`MINIMAL_LEXICON` aus der Factory.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && .venv/bin/python -m pytest tests/test_course_review.py -q -p no:cacheprovider`
Expected: FAIL — `build_review_round` nimmt keinen Index und liefert kein `items`.

- [ ] **Step 3: Write the implementation**

`backend/app/course/review.py` — `_due_refs` bleibt, `build_review_round` wird ersetzt:

```python
def _pairs_item(course: Course, refs: list[TokenRef], *, today: str) -> dict:
    right_order = shuffled_order(f"review:{today}", len(refs))
    return {
        "kind": "pairs",
        "left": [
            {
                "index": index,
                "ref": f"{ref[0]}:{ref[1]}",
                "text": course.form(ref).text,
                "translit": course.form(ref).translit,
            }
            for index, ref in enumerate(refs)
        ],
        "right": [
            {"index": index, "gloss_de": course.gloss(refs[position])}
            for index, position in enumerate(right_order)
        ],
    }


def build_review_round(
    conn: Connection,
    course: Course,
    index: ReviewIndex,
    *,
    today: str,
    size: int = 5,
) -> dict:
    """Faellige Formen, wo moeglich in einer echten Kursaufgabe."""
    refs = _due_refs(conn, course, today=today, size=size)
    allowed = set(progress_repo.all_progress(conn))

    items: list[dict] = []
    leftovers: list[TokenRef] = []
    for ref in refs:
        location = index.pick(ref, allowed_units=allowed, seed=f"review:{today}")
        if location is None:
            leftovers.append(ref)
            continue
        unit_id, exercise_id = location
        exercise = next(
            item for item in course.units[unit_id].exercises if item.id == exercise_id
        )
        items.append(
            {
                "kind": "exercise",
                "unit_id": unit_id,
                "exercise_id": exercise_id,
                "ref": f"{ref[0]}:{ref[1]}",
                **present_exercise(course, exercise),
            }
        )

    # Eine Zuordnung mit einem Paar ist keine Aufgabe: dann kommt eine weitere
    # faellige Form dazu, auch wenn sie eine Kontext-Aufgabe haette.
    if len(leftovers) == 1 and items:
        borrowed = items.pop()
        lexeme_id, form_key = borrowed["ref"].split(":", 1)
        leftovers.append((lexeme_id, form_key))

    if len(leftovers) >= 2:
        items.append(_pairs_item(course, leftovers, today=today))

    return {"items": items}
```

Importe ergänzen: `from app.course.presenter import present_exercise`,
`from app.course.review_index import ReviewIndex`, `from app.repositories import progress_repo`.

**Wichtig für `grade_review_round`:** Es baut die Zuordnung heute aus `_due_refs`. Damit es dieselben
Formen sieht, muss es dieselbe Auswahl treffen. Daher bekommt es denselben Aufbau: `_due_refs`, dann
Index-Abfrage, dann die Übriggebliebenen — die Funktion wird um einen `index`-Parameter erweitert und
benutzt eine gemeinsame Hilfe `_leftover_refs(conn, course, index, today=..., size=...)`, die beide
Seiten teilen. Sonst bewertet die Runde andere Formen, als sie gestellt hat.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && .venv/bin/python -m pytest -q -p no:cacheprovider`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/course/review.py backend/tests/test_course_review.py
git commit -m "feat(review): build rounds from real exercises with a matching fallback"
```

---

### Task 3: Der Endpunkt

**Files:**
- Modify: `backend/app/course/service.py`, `backend/app/api/routes.py`, `backend/app/api/schemas.py`
- Test: `backend/tests/test_course_service.py`, `backend/tests/test_routes.py`

**Interfaces:**
- Produces:
  - `service.submit_review_exercise(conn, course, *, unit_id, exercise_id, submission, today=None) -> AnswerOutcome`
  - `POST /api/review/exercise` mit `{unit_id, exercise_id, submission}`

- [ ] **Step 1: Write the failing test**

```python
def test_wiederholung_bewertet_und_plant_fort(conn, tmp_path):
    course = load_course(write_course(tmp_path))
    exercise = course.units[1].exercises[1]
    options = choose_form_options(course, exercise)
    richtige = options.index(exercise.answer)

    outcome = service.submit_review_exercise(
        conn, course, unit_id=1, exercise_id="1-2",
        submission={"option_index": richtige}, today="2026-01-02",
    )
    assert outcome.correct is True
    zustand = lexeme_srs_repo.get_state(conn, lexeme_id="delat", form_key="prs.1sg")
    assert zustand is not None, "die Form muss fortgeschrieben sein"


def test_wiederholung_ruehrt_den_einheiten_fortschritt_nicht_an(conn, tmp_path):
    # Die wichtigste Zusage: eine falsche Wiederholung darf eine abgeschlossene
    # Einheit nicht wieder aufreissen.
    course = load_course(write_course(tmp_path))
    progress_repo.bump_progress(conn, unit_id=1, correct=True)
    vorher = progress_repo.get_progress(conn, 1)

    service.submit_review_exercise(
        conn, course, unit_id=1, exercise_id="1-2",
        submission={"option_index": 99}, today="2026-01-02",
    )

    nachher = progress_repo.get_progress(conn, 1)
    assert (nachher.correct_count, nachher.total_count, nachher.status) == (
        vorher.correct_count, vorher.total_count, vorher.status
    )
    assert progress_repo.attempt_count(conn, 1) == 0, "kein Versuch darf protokolliert werden"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && .venv/bin/python -m pytest tests/test_course_service.py -q -p no:cacheprovider`
Expected: FAIL — `submit_review_exercise` existiert nicht.

- [ ] **Step 3: Write the implementation**

In `backend/app/course/service.py`:

```python
def submit_review_exercise(
    conn: Connection,
    course: Course,
    *,
    unit_id: int,
    exercise_id: str,
    submission: dict,
    today: str | None = None,
) -> AnswerOutcome:
    """Eine Kursaufgabe in der Wiederholung bewerten.

    Bewusst ohne `bump_progress` und `record_attempt`: beide haengen an der
    Einheit, und eine falsch beantwortete Wiederholung darf eine laengst
    abgeschlossene Einheit nicht wieder aufreissen.
    """
    unit = course.units[unit_id]
    exercise = next((item for item in unit.exercises if item.id == exercise_id), None)
    if exercise is None:
        raise KeyError(f"Aufgabe {exercise_id!r} gehört nicht zu Einheit {unit_id}")

    result = check_answer(course, exercise, submission)
    day = _today(today)
    for ref in result.trained_forms:
        schedule_form(conn, ref, correct=result.correct, today=day)

    return AnswerOutcome(
        correct=result.correct,
        solution_text=result.solution_text,
        solution_translit=result.solution_translit,
        solution_audio=result.solution_audio,
        explanation_de=result.explanation_de,
        unit_completed=False,
        correct_count=0,
        total_count=0,
    )
```

In `schemas.py`:

```python
class ReviewExerciseRequest(BaseModel):
    unit_id: int
    exercise_id: str
    submission: dict
```

In `routes.py`:

```python
@router.post("/review/exercise", response_model=AnswerResponse)
def review_exercise(
    payload: ReviewExerciseRequest,
    conn: Connection = Depends(get_db),
    course: Course = Depends(get_course),
) -> AnswerResponse:
    try:
        outcome = course_service.submit_review_exercise(
            conn,
            course,
            unit_id=payload.unit_id,
            exercise_id=payload.exercise_id,
            submission=payload.submission,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return AnswerResponse(**vars(outcome))
```

Und `review_due` bzw. `review_answer` bekommen `index: ReviewIndex = Depends(get_review_index)`
durchgereicht.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && .venv/bin/python -m pytest -q -p no:cacheprovider`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app backend/tests
git commit -m "feat(review): grade a course exercise without touching unit progress"
```

---

### Task 4: Ein Test gegen den echten Kurs

**Files:**
- Modify: `backend/tests/test_real_content.py`

- [ ] **Step 1: Write the failing test**

```python
def test_der_index_findet_fuer_die_meisten_wortformen_eine_kontext_aufgabe():
    # Ohne diesen Test koennte eine Content-Aenderung die Kontext-Wiederholung
    # still aushebeln. Buchstaben zaehlen nicht mit: sie stehen in keinem Satz.
    from app.content.validator import _exercise_tokens
    from app.course.review_index import build_index

    course = load_course(CONTENT_DIR)
    index = build_index(course)

    formen = {
        ref
        for unit in course.ordered_units()
        for exercise in unit.exercises
        for ref in _exercise_tokens(exercise)
        if course.lexemes[ref[0]].pos != "letter"
    }
    mit_kontext = {ref for ref in formen if ref in index.exact or ref in index.broad}
    anteil = len(mit_kontext) / len(formen)
    assert anteil >= 0.6, f"nur {anteil:.0%} der Wortformen haben eine Kontext-Aufgabe"


def test_buchstaben_haben_keine_kontext_aufgabe():
    # Sie sollen es auch nicht: fuer sie ist die Zuordnung die richtige Form.
    from app.course.review_index import build_index

    course = load_course(CONTENT_DIR)
    index = build_index(course)
    buchstaben = {
        ref for ref in (index.exact | index.broad) if course.lexemes[ref[0]].pos == "letter"
    }
    assert buchstaben == set()
```

- [ ] **Step 2: Run test to verify it fails or passes**

Run: `cd backend && .venv/bin/python -m pytest tests/test_real_content.py -q -p no:cacheprovider`
Expected: PASS — gemessen liegt der Anteil bei rund 69 %. Der Test hält den Stand fest, statt ihn zu
erzeugen.

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_real_content.py
git commit -m "test(content): pin how much of the course can be reviewed in context"
```

---

### Task 5: Der Fehler-Nachlauf

**Files:**
- Modify: `frontend/src/views/UnitView.tsx`, `frontend/src/views/UnitView.test.tsx`

**Interfaces:**
- Kein Backend-Anteil.

- [ ] **Step 1: Write the failing test**

```tsx
describe("UnitView — Fehler-Nachlauf", () => {
  beforeEach(() => vi.restoreAllMocks());

  it("bringt eine falsch beantwortete Aufgabe am Ende wieder", async () => {
    vi.spyOn(api, "getUnit").mockResolvedValue(unit);
    vi.spyOn(api, "submitAnswer").mockResolvedValue({
      correct: false,
      solution_text: "до свида́ния",
      solution_translit: "do svidánija",
      solution_audio: ["до свида́ния"],
      explanation_de: "",
      unit_completed: false,
      correct_count: 0,
      total_count: 2,
    });
    renderUnit();

    fireEvent.click(await screen.findByRole("button", { name: "Los geht's" }));
    // Erste Aufgabe falsch beantworten
    fireEvent.click(await screen.findByRole("button", { name: /свида́ния/ }));
    fireEvent.click(screen.getByRole("button", { name: "Prüfen" }));
    fireEvent.click(await screen.findByRole("button", { name: "Weiter" }));

    // Zweite Aufgabe, dann muss die erste wiederkommen statt „geschafft"
    fireEvent.click(await screen.findByRole("button", { name: /спаси́бо/ }));
    fireEvent.click(screen.getByRole("button", { name: "Prüfen" }));
    fireEvent.click(await screen.findByRole("button", { name: "Weiter" }));

    expect(await screen.findByText(/Noch einmal/)).toBeInTheDocument();
    expect(screen.queryByText("Einheit geschafft!")).toBeNull();
  });

  it("zählt Wiederholungen nicht als Fortschritt", async () => {
    vi.spyOn(api, "getUnit").mockResolvedValue(unit);
    vi.spyOn(api, "submitAnswer").mockResolvedValue({
      correct: false,
      solution_text: "до свида́ния",
      solution_translit: "do svidánija",
      solution_audio: [],
      explanation_de: "",
      unit_completed: false,
      correct_count: 0,
      total_count: 2,
    });
    renderUnit();

    fireEvent.click(await screen.findByRole("button", { name: "Los geht's" }));
    expect(screen.getByText(/Aufgabe 1 von 2/)).toBeInTheDocument();

    fireEvent.click(await screen.findByRole("button", { name: /свида́ния/ }));
    fireEvent.click(screen.getByRole("button", { name: "Prüfen" }));
    fireEvent.click(await screen.findByRole("button", { name: "Weiter" }));

    // Falsch beantwortet heisst: nicht weitergekommen.
    expect(screen.getByText(/Aufgabe 1 von 2/)).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test --prefix frontend -- UnitView`
Expected: FAIL — die Einheit meldet „geschafft".

- [ ] **Step 3: Write the implementation**

In `UnitView.tsx` `position` durch eine Warteschlange ersetzen:

```tsx
  const [queue, setQueue] = useState<string[] | null>(null);
  const [solved, setSolved] = useState<Set<string>>(new Set());
  const [repeating, setRepeating] = useState(false);
```

Beim Laden der Einheit `setQueue(unit.exercises.map((item) => item.id))`.

`advance` wird zu:

```tsx
  const advance = () => {
    const wasCorrect = result?.correct === true;
    setResult(null);
    setQueue((current) => {
      if (!current) return current;
      const [head, ...rest] = current;
      // Richtig: raus. Falsch: ans Ende, damit sie wiederkommt.
      const next = wasCorrect ? rest : [...rest, head];
      if (next.length === 0) setPhase("done");
      setRepeating(next.length > 0 && !wasCorrect && rest.includes(next[0]) === false);
      return next;
    });
    if (wasCorrect) setSolved((current) => new Set(current).add(exercise.id));
  };
```

Einfacher und ohne die verschachtelte Bedingung: `repeating` wird direkt aus der Schlange abgeleitet —
eine Aufgabe ist eine Wiederholung, wenn sie schon einmal falsch beantwortet wurde. Dafür ein Set
`missed`:

```tsx
  const [missed, setMissed] = useState<Set<string>>(new Set());
  // beim Bewerten: if (!result.correct) setMissed(current => new Set(current).add(exercise.id));
  const isRepeat = missed.has(exercise.id);
```

Der Fortschrittszähler:

```tsx
      <p className="text-sm text-slate-500">
        Aufgabe {solved.size + 1} von {unit.exercises.length}
      </p>
      {isRepeat ? (
        <p className="text-sm text-amber-700">
          Noch einmal — beim letzten Mal hat es nicht gestimmt.
        </p>
      ) : null}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `npm test --prefix frontend` und `cd frontend && npx tsc --noEmit -p tsconfig.json`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/views/UnitView.tsx frontend/src/views/UnitView.test.tsx
git commit -m "feat(course): replay wrong exercises until they are right"
```

---

### Task 6: Die Wiederholung im Frontend

**Files:**
- Modify: `frontend/src/views/ReviewView.tsx`, `frontend/src/views/ReviewView.test.tsx`, `frontend/src/courseTypes.ts`, `frontend/src/courseApi.ts`

**Interfaces:**
- Consumes: `GET /api/review/due` mit `items` (Task 2), `POST /api/review/exercise` (Task 3)
- Produces: `submitReviewExercise(unitId: number, exerciseId: string, submission: Submission): Promise<AnswerResult>`

- [ ] **Step 1: Write the failing test**

```tsx
it("löst eine echte Kursaufgabe in der Wiederholung", async () => {
  vi.spyOn(api, "getReviewRound").mockResolvedValue({
    items: [
      {
        kind: "exercise",
        unit_id: 8,
        exercise_id: "8-4",
        ref: "govorit:prs.1sg",
        id: "8-4",
        type: "choose_form",
        prompt_de: "Welche Endung passt zu я?",
        audio_prompt: false,
        sentence: [{ text: "я", translit: "ja" }, null],
        options: [{ index: 0, text: "говорю́", translit: "govorjú" }],
      },
    ],
  });
  const submit = vi.spyOn(api, "submitReviewExercise").mockResolvedValue({
    correct: true,
    solution_text: "говорю́",
    solution_translit: "govorjú",
    solution_audio: ["говорю́"],
    explanation_de: "",
    unit_completed: false,
    correct_count: 0,
    total_count: 0,
  });

  render(<ReviewView />);
  fireEvent.click(await screen.findByRole("button", { name: /говорю́/ }));

  await waitFor(() =>
    expect(submit).toHaveBeenCalledWith(8, "8-4", { option_index: 0 }),
  );
});

it("meldet, wenn nichts fällig ist", async () => {
  vi.spyOn(api, "getReviewRound").mockResolvedValue({ items: [] });
  render(<ReviewView />);
  expect(await screen.findByText(/nichts zu wiederholen/i)).toBeInTheDocument();
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test --prefix frontend -- ReviewView`
Expected: FAIL — `submitReviewExercise` gibt es nicht, `items` wird nicht gelesen.

- [ ] **Step 3: Write the implementation**

In `courseTypes.ts`:

```ts
export type ReviewItem =
  | ({ kind: "exercise"; unit_id: number; exercise_id: string; ref: string } & Exercise)
  | { kind: "pairs"; left: (Tile & { ref: string })[]; right: GlossOption[] };

export interface ReviewRound {
  items: ReviewItem[];
}
```

In `courseApi.ts`:

```ts
export const submitReviewExercise = (
  unitId: number,
  exerciseId: string,
  submission: Submission,
): Promise<AnswerResult> =>
  post("/api/review/exercise", {
    unit_id: unitId,
    exercise_id: exerciseId,
    submission,
  });
```

(Die genaue Form von `post` aus der Datei übernehmen — dort steht bereits ein Muster für `submitAnswer`.)

`ReviewView` läuft mit einem Index durch `round.items`: bei `kind === "exercise"` rendert es
`ExerciseRunner` und schickt an `submitReviewExercise`, bei `kind === "pairs"` `MatchPairsExercise`
und `submitReviewRound` wie bisher. Ergebnisse werden gesammelt und am Ende zusammen gezeigt.

- [ ] **Step 4: Run tests to verify they pass**

Run: `npm test --prefix frontend` und `cd frontend && npx tsc --noEmit -p tsconfig.json`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src
git commit -m "feat(review): walk the round as a sequence of real exercises"
```

---

### Task 7: e2e und Abschlussprüfung

**Files:**
- Modify: `frontend/e2e/kurs.spec.ts`

- [ ] **Step 1: Write the failing test**

```ts
test("bringt eine falsch beantwortete Aufgabe wieder", async ({ page }) => {
  await page.goto("/kurs/8");
  await startExercises(page);

  // Erste Aufgabe absichtlich falsch: irgendein falsches Paar zuordnen.
  const cards = page.locator("main .grid > button");
  const count = (await cards.count()) / 2;
  await cards.nth(0).click();
  await cards.nth(count + 1).click();

  await expect(page.getByTestId("feedback")).toBeVisible();
  await expect(page.getByText(/Aufgabe 1 von/)).toBeVisible();
});
```

- [ ] **Step 2: Run the whole suite**

```bash
make test
make test-e2e
make validate
```

Expected: alles grün.

- [ ] **Step 3: Deploy and check by hand**

```bash
make deploy
make smoke
```

Dann eine Einheit öffnen, absichtlich falsch antworten und prüfen, dass die Aufgabe am Ende
wiederkommt; danach `/wiederholen` öffnen und sehen, ob eine echte Kursaufgabe erscheint.

- [ ] **Step 4: Commit**

```bash
git add frontend/e2e
git commit -m "test(e2e): cover the mistake replay in a unit"
```

---

## Selbstprüfung des Plans

**Spec-Abdeckung**

| Spec-Abschnitt | Task |
|---|---|
| 3 Index, genau/weit, Fortschrittsfilter, Los | 1 |
| 4 Runde, ein Zuordnungs-Eintrag, Ein-Paar-Fall | 2 |
| 5 Endpunkt ohne Einheiten-Buchführung | 3 |
| 6 Fehler-Nachlauf, Zähler, Hinweis | 5 |
| 7 Frontend der Wiederholung | 6 |
| 8 Tests | 1–7, echter Kurs in 4 |

**Was der Plan über die Spec hinaus festlegt**

1. **`grade_review_round` bekommt den Index.** Die Spec sagt „bleibt unverändert" — das stimmt nicht:
   es baut die Zuordnung aus `_due_refs`, und wenn `build_review_round` inzwischen einen Teil der
   Formen als Aufgaben abzweigt, sähe die Bewertung andere Formen als die Runde gestellt hat. Beide
   teilen sich deshalb eine Hilfe `_leftover_refs`.
2. **`AnswerOutcome` wird für die Wiederholung mit `unit_completed=False` und Nullzählern gefüllt.**
   Die Felder gehören zur Einheit und haben hier keine Bedeutung; sie bleiben in der Antwort, damit
   das Schema eines bleibt.
3. **`missed` als Set statt einer Ableitung aus der Schlange.** Ob eine Aufgabe eine Wiederholung ist,
   lässt sich aus der Schlange allein nicht sauber ablesen.

**Typkonsistenz geprüft:** `Location = tuple[int, str]` (Task 1) → `unit_id`/`exercise_id` in der
Runde (Task 2) → `ReviewExerciseRequest` (Task 3) → `submitReviewExercise(unitId, exerciseId, …)`
(Task 6); `ref` durchgängig als `"lexeme:form"`-Zeichenkette.
