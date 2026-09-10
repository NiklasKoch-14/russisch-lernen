# Hörgespräche — Umsetzungsplan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ein eigener Tab „Hören", in dem zwei Figuren mit zwei Stimmen ein Gespräch führen, der Lernende blind zuhört und danach sagt, worum es ging.

**Architecture:** Gespräche sind versionierte JSON-Dateien unter `content/ru/dialogs/`, geladen und geprüft im selben Durchgang wie der Kurs. Ein Auswahlmodul zieht das am längsten nicht gehörte freigeschaltete Gespräch, mischt die Antwortoptionen aus einem Seed und behält `correct_index` beim Server. Der `tts`-Dienst hält zwei Piper-Modelle und nimmt die Stimme je Anfrage entgegen.

**Tech Stack:** FastAPI + SQLite, React/Vite + Tailwind, Piper (ONNX), pytest, vitest, Playwright.

**Spec:** `docs/superpowers/specs/2026-09-10-speaker-listening-dialogs-design.md`

## Global Constraints

- Alle Texte in der App, alle Kommentare, alle Commit-Nachrichten sind deutsch; Bezeichner im Code englisch.
- Lerninhalt ist niemals LLM-Ausgabe. Sätze stehen als `(lexeme_id, form_key)`-Paare.
- Lösungen verlassen den Server nie: `correct_index` wird nur in der Antwort auf einen Versuch zurückgegeben.
- Kein Gespräch benutzt ein Lexem, das nicht bis `min_unit` eingeführt wurde.
- Der dreistufige Tonrückfall (Piper → Browserstimme → Textfassung) bleibt heil.
- Betonung `U+0301` gehört in den Inhalt, nie in die Piper-Anfrage (`strip_stress`).
- Prüfläufe: `make validate`, `make test`, `make test-e2e` (nie `make test-e2e-show`).
- Backend-Tests laufen mit `cd backend && .venv/bin/pytest -q -p no:cacheprovider`.

---

### Task 1: Zweite Stimme im tts-Dienst

**Files:**
- Modify: `tts/app.py`
- Modify: `tts/Dockerfile`
- Modify: `docker-compose.yml`
- Test: `tts/tests/test_app.py`

**Interfaces:**
- Produces: `POST /synthesize {text, voice?}` mit `voice ∈ {"m","f"}`, Vorgabe `"m"`; `GET /health → {status, voice, voices: {"m": name, "f": name|null}}`.

- [ ] **Step 1: Failing tests schreiben**

```python
def test_synthesize_nimmt_die_weibliche_stimme(client):
    response = client.post("/synthesize", json={"text": "дом", "voice": "f"})
    assert response.status_code == 200
    assert response.content.startswith(b"RIFF")


def test_unbekannte_stimme_faellt_auf_die_vorgabe_zurueck(client, gesprochen):
    client.post("/synthesize", json={"text": "дом", "voice": "x"})
    assert gesprochen[-1][1] == "ru_RU-denis-medium"


def test_health_nennt_beide_stimmen(client):
    body = client.get("/health").json()
    assert body["voices"]["m"] == "ru_RU-denis-medium"
    assert body["voices"]["f"] == "ru_RU-irina-medium"
```

Die Attrappe muss dafür die Stimme mitschneiden — `synthesize_wav(text, voice_name)` statt `synthesize_wav(text)`:

```python
@pytest.fixture
def gesprochen():
    return []


@pytest.fixture
def client(monkeypatch, gesprochen):
    import app as module

    def fake_synthesize(text: str, voice_name: str) -> bytes:
        gesprochen.append((text, voice_name))
        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(22050)
            wav.writeframes(b"\x00\x00" * len(text))
        return buffer.getvalue()

    monkeypatch.setattr(module, "synthesize_wav", fake_synthesize)
    return TestClient(module.app)
```

- [ ] **Step 2: Lauf, der fehlschlägt**

Run: `cd backend && .venv/bin/pytest ../tts/tests -q -p no:cacheprovider`
Expected: FAIL — `synthesize_wav()` nimmt nur ein Argument, `voices` fehlt in `/health`.

- [ ] **Step 3: `tts/app.py` umbauen**

```python
VOICES = {
    "m": os.environ.get("PIPER_VOICE", "ru_RU-denis-medium"),
    "f": os.environ.get("PIPER_VOICE_FEMALE", "ru_RU-irina-medium"),
}
DEFAULT_ROLE = "m"
MODEL_DIR = os.environ.get("PIPER_MODEL_DIR", "/models")

_loaded: dict[str, object] = {}


def voice_name(role: str | None) -> str:
    """Rolle auf den Modellnamen abbilden — unbekannt heisst Vorgabestimme.

    Bewusst kein Fehler: eine fehlende zweite Stimme darf ein Gespräch
    höchstens eintönig machen, nie unhörbar.
    """
    return VOICES.get(role or DEFAULT_ROLE, VOICES[DEFAULT_ROLE])


def _load_voice(name: str):
    if name not in _loaded:
        from piper import PiperVoice

        path = os.path.join(MODEL_DIR, f"{name}.onnx")
        if not os.path.exists(path):
            name = VOICES[DEFAULT_ROLE]
            path = os.path.join(MODEL_DIR, f"{name}.onnx")
        _loaded[name] = PiperVoice.load(path)
    return _loaded[name]


def synthesize_wav(text: str, voice_name_: str) -> bytes:
    from piper import SynthesisConfig

    voice = _load_voice(voice_name_)
    ...


class SynthesizeRequest(BaseModel):
    text: str
    voice: str | None = None


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "voice": VOICES[DEFAULT_ROLE], "voices": _available()}
```

`_available()` prüft je Rolle, ob `<MODEL_DIR>/<name>.onnx` existiert, und gibt `None` für das, was fehlt.

- [ ] **Step 4: Tests grün**

Run: `cd backend && .venv/bin/pytest ../tts/tests -q -p no:cacheprovider`
Expected: PASS

- [ ] **Step 5: Dockerfile und Compose**

`tts/Dockerfile`: zweites `ARG PIPER_VOICE_FEMALE=ru_RU-irina-medium`, beide Modelle in einem `RUN`-Schritt laden, `PIPER_MODEL_DIR=/models` setzen (statt `PIPER_MODEL_PATH`).
`docker-compose.yml`: `PIPER_VOICE_FEMALE` als build-arg und Umgebungsvariable beim `tts`-Dienst **und** beim `backend` (Kommentar über die Übereinstimmung erweitern).

- [ ] **Step 6: Commit**

```bash
git add tts docker-compose.yml
git commit -m "feat(tts): zweite Stimme je Anfrage"
```

---

### Task 2: `/api/audio?voice=` im Backend

**Files:**
- Modify: `backend/app/config.py`, `backend/app/tts_client.py`, `backend/app/api/routes.py:314-352`
- Test: `backend/tests/test_audio_route.py` (vorhanden, sonst anlegen)

**Interfaces:**
- Consumes: `POST /synthesize {text, voice}` aus Task 1.
- Produces: `GET /api/audio?text=…&voice=m|f`; `TtsClient.synthesize(text, voice="m")`; `settings.piper_voice_female`.

- [ ] **Step 1: Failing tests**

```python
def test_audio_reicht_die_stimme_an_den_dienst_weiter(client, tts_stub):
    client.get("/api/audio", params={"text": "дом", "voice": "f"})
    assert tts_stub.calls[-1]["voice"] == "f"


def test_audio_trennt_die_stimmen_im_zwischenspeicher(client, tts_stub):
    client.get("/api/audio", params={"text": "дом", "voice": "m"})
    client.get("/api/audio", params={"text": "дом", "voice": "f"})
    assert len(tts_stub.calls) == 2


def test_unbekannte_stimme_ist_ein_fehler(client):
    assert client.get("/api/audio", params={"text": "дом", "voice": "x"}).status_code == 422
```

- [ ] **Step 2: Lauf, der fehlschlägt**

Run: `cd backend && .venv/bin/pytest tests/test_audio_route.py -q -p no:cacheprovider`
Expected: FAIL — `voice` wird nicht angenommen.

- [ ] **Step 3: Umsetzen**

```python
# config.py
piper_voice_female: str = os.environ.get("PIPER_VOICE_FEMALE", "ru_RU-irina-medium")

# routes.py
VOICE_MODELS = {"m": settings.piper_voice, "f": settings.piper_voice_female}

@router.get("/audio")
def audio(
    text: str = Query(...),
    voice: Literal["m", "f"] = Query("m"),
    ...
):
    ...
    key = audio_key(cleaned, voice=VOICE_MODELS[voice], length_scale=settings.piper_length_scale)
    ...
        data = tts.synthesize(cleaned, voice=voice)
```

`TtsClient.synthesize(self, text: str, voice: str = "m")` schickt `{"text": text, "voice": voice}`.

- [ ] **Step 4: Tests grün**

Run: `cd backend && .venv/bin/pytest tests/test_audio_route.py -q -p no:cacheprovider`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app backend/tests
git commit -m "feat(audio): Stimme als Parameter der Tonroute"
```

---

### Task 3: Stimme im Frontend durchreichen

**Files:**
- Modify: `frontend/src/audio/serverSpeech.ts`, `frontend/src/audio/SpeechContext.tsx`
- Test: `frontend/src/audio/serverSpeech.test.ts`

**Interfaces:**
- Produces: `playAudio(text, { slow?, voice? })`, `audioUrl(text, voice?)`, `prefetchAudio(text, voice?)`, `say(text, { slow?, voice? })` mit `voice: "m" | "f"`.

- [ ] **Step 1: Failing test**

```ts
it("hängt die Stimme an die Adresse", () => {
  expect(audioUrl("дом", "f")).toContain("voice=f");
});

it("hält die Stimmen im Speicher auseinander", async () => {
  await prefetchAudio("дом", "m");
  await prefetchAudio("дом", "f");
  expect(fetchMock).toHaveBeenCalledTimes(2);
});
```

- [ ] **Step 2: Lauf, der fehlschlägt**

Run: `cd frontend && npx vitest run src/audio/serverSpeech.test.ts`
Expected: FAIL

- [ ] **Step 3: Umsetzen** — `voice` wandert in die URL und damit automatisch in den Speicher-Schlüssel (`pending` ist nach URL indiziert). `SpeechContext.say` reicht `voice` an `playAudio` durch; die Browserstimme ignoriert ihn (eine Stimme für alle Rollen).

- [ ] **Step 4: Tests grün**

Run: `cd frontend && npx vitest run src/audio`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/audio
git commit -m "feat(audio): Stimme bis zur Wiedergabe durchreichen"
```

---

### Task 4: Gespräche als Inhalt — Modelle, Lader, Validator

**Files:**
- Modify: `backend/app/content/models.py`, `backend/app/content/loader.py`, `backend/app/content/validator.py`
- Create: `content/ru/dialogs/001.json`, `002.json`, `003.json`
- Test: `backend/tests/test_dialog_content.py`

**Interfaces:**
- Produces: `Dialog(id, min_unit, title_de, speakers, lines, question_de, options_de, correct_index)`, `DialogSpeaker(name_ru, name_de, voice)`, `DialogLine(speaker, tokens, translation_de)`; `Course.dialogs: dict[int, Dialog]`; `load_course` liest `dialogs/*.json`; `validate_course` prüft sie mit.

- [ ] **Step 1: Failing tests** (je Regel aus Abschnitt 10 der Spec eine negative Prüfung)

```python
def test_lader_liest_gespraeche(course):
    dialog = course.dialogs[1]
    assert dialog.min_unit >= 1
    assert len(dialog.speakers) >= 2
    assert dialog.lines[0].speaker in range(len(dialog.speakers))


def test_wort_nach_min_unit_ist_ein_fehler(course_factory):
    course = course_factory(dialog_uses=("platit", "inf"), min_unit=12)
    fehler = validate_course(course)
    assert any("plati" in f and "Gespräch 1" in f for f in fehler)


def test_sprecherindex_ausserhalb_ist_ein_fehler(course_factory): ...
def test_doppelte_option_ist_ein_fehler(course_factory): ...
def test_zwei_zeilen_sind_zu_wenig(course_factory): ...
def test_leere_uebersetzung_ist_ein_fehler(course_factory): ...
def test_unbekannte_stimme_ist_ein_fehler(course_factory): ...
def test_luecke_in_den_ids_ist_ein_fehler(course_factory): ...
```

- [ ] **Step 2: Lauf, der fehlschlägt**

Run: `cd backend && .venv/bin/pytest tests/test_dialog_content.py -q -p no:cacheprovider`
Expected: FAIL — `Course` hat kein `dialogs`.

- [ ] **Step 3: Modelle und Lader**

```python
@dataclass(frozen=True)
class DialogSpeaker:
    name_ru: str
    name_de: str
    voice: str
    """"m" oder "f" — welches Piper-Modell dahintersteht, entscheidet die Konfiguration."""


@dataclass(frozen=True)
class DialogLine:
    speaker: int
    tokens: list[TokenRef]
    translation_de: str


@dataclass(frozen=True)
class Dialog:
    id: int
    min_unit: int
    title_de: str
    speakers: list[DialogSpeaker]
    lines: list[DialogLine]
    question_de: str
    options_de: list[str]
    correct_index: int
```

`load_course` liest `sorted((root / "dialogs").glob("*.json"))`; fehlt das Verzeichnis, bleibt `dialogs` leer.

- [ ] **Step 4: Validator**

Neue Funktion `_check_dialogs(course)`, aufgerufen in `validate_course`. Für die `min_unit`-Regel wird einmal die Menge der bis dahin eingeführten Lexeme gebildet:

```python
def _introduced_by(course: Course) -> dict[int, set[str]]:
    """Je Einheit: welche Lexeme sind bis dahin eingeführt?"""
    seen: set[str] = set()
    result: dict[int, set[str]] = {}
    for unit in course.ordered_units():
        seen.update(unit.new_lexemes)
        result[unit.id] = set(seen)
    return result
```

Meldungen deutsch, im Ton der bestehenden: `f"Gespräch {dialog.id}, Zeile {index}: Lexem {lexeme_id!r} ist in Einheit {dialog.min_unit} noch nicht eingeführt"`.

- [ ] **Step 5: Drei Beispielgespräche** — Nr. 1 (`min_unit` 12, 3 Zeilen), Nr. 2 (`min_unit` 25, 4 Zeilen), Nr. 3 (`min_unit` 44, 8 Zeilen). Danach `make validate`.

- [ ] **Step 6: Tests grün**

Run: `cd backend && .venv/bin/pytest tests/test_dialog_content.py -q -p no:cacheprovider && make validate`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add backend/app/content backend/tests content/ru/dialogs
git commit -m "feat(content): Hörgespräche als geprüfter Inhalt"
```

---

### Task 5: Auswahl, Speicher und Routen

**Files:**
- Modify: `backend/app/db.py` (Tabelle), `backend/app/api/routes.py`, `backend/app/api/schemas.py`
- Create: `backend/app/course/listening.py`, `backend/app/repositories/listening_repo.py`
- Test: `backend/tests/test_listening_service.py`, `backend/tests/test_listening_routes.py`

**Interfaces:**
- Consumes: `Course.dialogs` (Task 4).
- Produces: `pick_dialog(course, conn, *, now) -> tuple[Dialog, str] | None`, `dialog_payload(course, dialog, seed) -> dict`, `check_answer(dialog, seed, option_index) -> tuple[bool, int]`, `listening_repo.record_run/last_played`, Routen `GET /api/listening/next` und `POST /api/listening/{id}/answer`.

- [ ] **Step 1: Failing tests**

```python
def test_nur_freigeschaltete_gespraeche(course, conn):
    # nichts abgeschlossen -> nichts wählbar
    assert pick_dialog(course, conn, now="2026-09-10T10:00:00") is None


def test_nimmt_das_am_laengsten_nicht_gehoerte(course, conn):
    complete_units(conn, upto=44)
    listening_repo.record_run(conn, dialog_id=1, correct=True, played_at="2026-09-09T10:00:00")
    dialog, _ = pick_dialog(course, conn, now="2026-09-10T10:00:00")
    assert dialog.id != 1


def test_einstufung_zaehlt_wie_abgeschlossen(course, conn):
    set_placement_unit(conn, 30)
    dialog, _ = pick_dialog(course, conn, now="2026-09-10T10:00:00")
    assert dialog.min_unit <= 29


def test_payload_verraet_die_loesung_nicht(course):
    payload = dialog_payload(course, course.dialogs[1], seed="s")
    assert "correct_index" not in payload
    assert "title_de" not in payload
    assert all("translation_de" not in line for line in payload["lines"])


def test_optionen_sind_nach_seed_gemischt_und_werden_wieder_aufgeloest(course):
    dialog = course.dialogs[1]
    payload = dialog_payload(course, dialog, seed="s")
    index = payload["options_de"].index(dialog.options_de[dialog.correct_index])
    correct, correct_index = check_answer(dialog, "s", index)
    assert correct and correct_index == index
```

- [ ] **Step 2: Lauf, der fehlschlägt**

Run: `cd backend && .venv/bin/pytest tests/test_listening_service.py -q -p no:cacheprovider`
Expected: FAIL — Modul fehlt.

- [ ] **Step 3: Umsetzen**

```python
def reached_unit(conn: Connection) -> int:
    """Bis wohin der Lernende kommt — abgeschlossen oder eingestuft.

    Wer sich einstufen lässt, hat die Einheiten davor nie angefasst und kann
    sie trotzdem; sonst bliebe der Tab für ihn leer.
    """
    completed = [p.unit_id for p in progress_repo.all_progress(conn).values()
                 if p.status == "completed"]
    profile = get_or_create_profile(conn)
    placed = (profile.placement_unit or 1) - 1
    return max([*completed, placed, 0])
```

`pick_dialog` sortiert die wählbaren nach `(zuletzt_gehört, id)` wie `pick_scene`; der Seed ist `f"{dialog.id}:{now}"`. `dialog_payload` mischt `options_de` mit `shuffled_order(f"{seed}:options", len(options))` und liefert je Zeile `speaker`, `text` (aus `course.form`) und `translit`. `check_answer` mischt dieselbe Reihenfolge und vergleicht.

- [ ] **Step 4: Tabelle und Routen**

`listening_runs` ans Ende von `SCHEMA` in `db.py`. Routen:

```python
@router.get("/listening/next", response_model=ListeningNextResponse)
def listening_next(course: Course = Depends(get_course), conn: Connection = Depends(get_db)):
    picked = listening.pick_dialog(course, conn, now=dt.datetime.now(dt.UTC).isoformat())
    if picked is None:
        return ListeningNextResponse(dialog_id=None, next_unit=listening.first_locked_unit(course))
    dialog, seed = picked
    return ListeningNextResponse(**listening.dialog_payload(course, dialog, seed))


@router.post("/listening/{dialog_id}/answer", response_model=ListeningAnswerResponse)
def listening_answer(dialog_id: int, payload: ListeningAnswerRequest, ...):
    dialog = course.dialogs.get(dialog_id)
    if dialog is None:
        raise HTTPException(status_code=404, detail="Gespräch gibt es nicht")
    correct, correct_index = listening.check_answer(dialog, payload.seed, payload.option_index)
    listening_repo.record_run(conn, dialog_id=dialog_id, correct=correct, played_at=...)
    return ListeningAnswerResponse(
        correct=correct, correct_index=correct_index, title_de=dialog.title_de,
        translations_de=[line.translation_de for line in dialog.lines],
    )
```

- [ ] **Step 5: Tests grün**

Run: `cd backend && .venv/bin/pytest tests/test_listening_service.py tests/test_listening_routes.py -q -p no:cacheprovider`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app backend/tests
git commit -m "feat(listening): Auswahl und Routen für Hörgespräche"
```

---

### Task 6: Der Tab „Hören"

**Files:**
- Modify: `frontend/src/courseTypes.ts`, `frontend/src/App.tsx`
- Create: `frontend/src/listeningApi.ts`, `frontend/src/views/ListeningView.tsx`, `frontend/src/listening/DialogPlayer.tsx`, `frontend/src/listening/DialogQuestion.tsx`, `frontend/src/listening/DialogTranscript.tsx`
- Test: `frontend/src/views/ListeningView.test.tsx`, `frontend/src/listening/DialogPlayer.test.tsx`

**Interfaces:**
- Consumes: `GET /api/listening/next`, `POST /api/listening/{id}/answer` (Task 5); `say(text, {voice})` (Task 3).
- Produces: Route `/hoeren` und ein fünfter Eintrag in `TABS`.

- [ ] **Step 1: Failing tests**

```tsx
it("zeigt vor der Antwort keinen russischen Text", async () => {
  render(<ListeningView />);
  expect(await screen.findByText("2 Sprecher · 3 Zeilen")).toBeInTheDocument();
  expect(screen.queryByText(/Как дела/)).not.toBeInTheDocument();
});

it("spielt die Zeilen nacheinander mit wechselnder Stimme", async () => {
  render(<ListeningView />);
  await userEvent.click(await screen.findByRole("button", { name: /abspielen/i }));
  await waitFor(() => expect(say).toHaveBeenCalledTimes(3));
  expect(say.mock.calls.map(([, options]) => options.voice)).toEqual(["m", "f", "m"]);
});

it("deckt Transkript und Übersetzung erst nach der Antwort auf", async () => { ... });

it("zeigt ohne Stimme sofort das Transkript", async () => { ... });
```

- [ ] **Step 2: Lauf, der fehlschlägt**

Run: `cd frontend && npx vitest run src/views/ListeningView.test.tsx`
Expected: FAIL — Datei fehlt.

- [ ] **Step 3: Typen und Api**

```ts
export interface ListeningSpeaker { name_ru: string; name_de: string; voice: "m" | "f" }
export interface ListeningLine { speaker: number; text: string; translit: string }
export interface ListeningDialog {
  dialog_id: number | null; next_unit?: number; seed: string;
  speakers: ListeningSpeaker[]; lines: ListeningLine[];
  question_de: string; options_de: string[];
}
export interface ListeningResult {
  correct: boolean; correct_index: number; title_de: string; translations_de: string[];
}
```

- [ ] **Step 4: Komponenten**

`DialogPlayer` spielt die Zeilen sequenziell (`for`-Schleife über `await say(line.text, { voice, slow })`), hält den laufenden Index im State für den leuchtenden Namens-Chip und bricht bei Pause ab. `DialogQuestion` rendert die Optionen wie `ListenMeaningExercise`. `DialogTranscript` nutzt `RussianText` für Umschrift-Treue. `ListeningView` hält die Phase (`listening | answering | revealed`).

- [ ] **Step 5: Tests grün**

Run: `cd frontend && npx vitest run src/views/ListeningView.test.tsx src/listening && npx tsc --noEmit`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add frontend/src
git commit -m "feat(listening): Tab Hören mit blindem Durchlauf"
```

---

### Task 7: Die siebzehn übrigen Gespräche

**Files:**
- Create: `content/ru/dialogs/004.json` … `020.json`
- Test: `backend/tests/test_real_content.py` (ein Testfall dazu)

- [ ] **Step 1: Failing test über die echten Inhalte**

```python
def test_jedes_gespraech_benutzt_nur_woerter_seiner_einheit():
    course = load_course(CONTENT_DIR)
    assert validate_course(course) == []
    assert len(course.dialogs) >= 20


def test_gespraeche_werden_mit_der_einheit_laenger():
    course = load_course(CONTENT_DIR)
    nach_einheit = sorted(course.dialogs.values(), key=lambda d: d.min_unit)
    laengen = [len(d.lines) for d in nach_einheit]
    assert laengen == sorted(laengen)
```

- [ ] **Step 2: Lauf, der fehlschlägt**

Run: `cd backend && .venv/bin/pytest tests/test_real_content.py -q -p no:cacheprovider -k gespraech`
Expected: FAIL — erst drei Gespräche.

- [ ] **Step 3: Gespräche schreiben** — Themen und Längen nach Abschnitt 11 der Spec. Nach jedem Viererblock `make validate` und die Sätze im Klartext rendern und Form für Form gegenlesen.

- [ ] **Step 4: Tests grün**

Run: `make validate && cd backend && .venv/bin/pytest -q -p no:cacheprovider`
Expected: PASS

- [ ] **Step 5: Commit** (ein Commit je Viererblock)

```bash
git add content/ru/dialogs backend/tests
git commit -m "feat(content): Hörgespräche 4 bis 8"
```

---

### Task 8: e2e und Dokumentation

**Files:**
- Create: `frontend/e2e/hoeren-dialoge.spec.ts`
- Modify: `CLAUDE.md`

- [ ] **Step 1: e2e-Test schreiben**

```ts
test("hört ein Gespräch, antwortet und liest nach", async ({ page }) => {
  await page.goto("/hoeren");
  await page.getByRole("button", { name: /abspielen/i }).click();
  await expect(page.getByText(/Sprecher ·/)).toBeVisible();
  await page.getByRole("button", { name: /Um den Einkauf/ }).click();
  await expect(page.getByText("Ich kaufe Brot und Käse.")).toBeVisible();
});
```

Der Testlauf braucht abgeschlossene Einheiten — der bestehende `seed`-Helfer der e2e-Suite setzt `placement_unit`.

- [ ] **Step 2: Lauf**

Run: `make test-e2e`
Expected: PASS

- [ ] **Step 3: `CLAUDE.md` ergänzen** — ein Absatz unter „Lerninhalte sind Daten": `content/ru/dialogs/NNN.json`, `min_unit` als Freischaltmarke, keine neuen Vokabeln, Stimme `m`/`f`.

- [ ] **Step 4: Commit**

```bash
git add frontend/e2e CLAUDE.md
git commit -m "test(listening): e2e-Lauf für den Hören-Tab"
```
