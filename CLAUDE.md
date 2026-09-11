# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Sprache

Der Nutzer ist deutschsprachig. Antworte auf Deutsch. Code-Kommentare, Commit-Nachrichten,
Entwurfsdokumente und alle Texte, die in der App erscheinen, sind ebenfalls deutsch — Bezeichner im
Code bleiben englisch. Fehlermeldungen des Content-Validators sind bewusst deutsch, weil sie beim
Schreiben von Lerninhalten gelesen werden.

## Befehle

`make help` listet alles. Die wichtigsten:

```bash
make deploy       # Container bauen und starten (Frontend 3000, Backend 8000)
make remove       # stoppen und entfernen — Volumes und damit der Lernfortschritt bleiben
make purge        # löscht auch die Volumes, fragt vorher nach
make validate     # Kursinhalte prüfen
make typecheck    # tsc --noEmit
make test         # typecheck + pytest (backend, tts) + vitest
make test-e2e     # Playwright headless
```

**Für eigene Prüfläufe immer `make test-e2e`, nie `make test-e2e-show`** — letzteres öffnet ein
sichtbares Chromium-Fenster auf dem Desktop des Nutzers und ist nur zum Zuschauen gedacht.

Einzelne Tests:

```bash
cd backend && .venv/bin/pytest tests/test_course_service.py -q -p no:cacheprovider
cd backend && .venv/bin/pytest -q -k primer          # nach Namen filtern
cd frontend && npx vitest run src/views/UnitView.test.tsx
cd frontend && npx playwright test e2e/kurs.spec.ts
```

`-p no:cacheprovider` unterdrückt Warnungen: das pytest-Cache-Verzeichnis ist nicht beschreibbar.

Das Backend nutzt ein vorhandenes `backend/.venv` (Abhängigkeiten in `backend/requirements.txt`).
Der `tts`-Dienst hat keine eigene Umgebung — seine Tests ersetzen Piper durch eine Attrappe und
laufen mit dem Interpreter des Backends.

Die Playwright-Tests starten Backend und Frontend selbst auf eigenen Ports (8001 und 5174) mit
frischer Datenbank. Ein laufender Stack wird weder gebraucht noch verändert.

## Architektur

Vier Container: `frontend` (React/Vite hinter nginx), `backend` (FastAPI + SQLite), `ollama`
(lokales Sprachmodell) und `tts` (Piper, ohne Port nach außen). Details zu Betrieb, Stimmen und
Lernablauf stehen im README.

### Lerninhalte sind Daten, kein Code und kein LLM-Output

Der gesamte Kurs liegt als versioniertes JSON unter `content/ru/` und wird beim Start read-only
geladen. **Das Sprachmodell erzeugt niemals Lerninhalt** und auch keine Fehlererklärung: die baut
`course/checker.py` aus den Formschlüsseln („das ist die er/sie-Form, hier steht die ich-Form"),
die Bezeichnungen stehen in `content/formkeys.py`. Grund: das lokale Modell ist bei russischer
Morphologie unzuverlässig. Im Kurs läuft es gar nicht mit, nur im alten freien Gespräch. SQLite
speichert ausschließlich Fortschritt.

- `lexicon.json` — jedes Lexem mit Formenparadigma, Betonungszeichen (U+0301), Umschrift, Bedeutung
- `units/NNN.json` — Alltagsszenario mit genau einem Grammatik-Fokus und 6–11 Aufgaben
- `primers.json` — deutsche Grundbegriffe (was ein Akkusativ ist), von Einheiten referenziert
- `screening.json` — die Sonden der Einstufung
- `dialogs/NNN.json` — Hörgespräche: zwei Figuren reden, der Lernende hört blind zu und sagt
  danach, worum es ging. `min_unit` ist die Einheit, ab der ein Gespräch offen ist; der Validator
  erzwingt, dass jedes benutzte Wort bis dahin eingeführt wurde. **Gespräche führen selbst keine
  Vokabeln ein.** Die Stimme einer Figur ist `m` oder `f` — welches Piper-Modell dahintersteht,
  entscheidet die Konfiguration

Sätze referenzieren **`(lexeme_id, form_key)`-Paare statt roher Zeichenketten**. Das ist die zentrale
Entwurfsentscheidung: nur dadurch lassen sich Inhalte maschinell prüfen, und die Ablenker beim
Aufgabentyp „Wortform wählen" entstehen automatisch aus dem Paradigma des richtigen Wortes.
Erlaubte Formschlüssel je Wortart stehen in `app/content/formkeys.py`.

Pfad durch den Code: `content/loader.py` → `content/models.py` (eingefrorene Dataclasses) →
`content/validator.py`. Der Loader ist streng und wirft `ContentError`; der Validator sammelt alle
Verstöße als deutsche Meldungen ein, statt beim ersten abzubrechen.

**Der Validator prüft Struktur, Betonung und Vokabelreihenfolge — nicht, ob ein russischer Satz
grammatisch stimmt.** Das bleibt Handarbeit. Ob die einzelnen Formen im Lexikon richtig gebildet
sind, prüft `content/morphology.py` gegen das Wörterbuch von pymorphy3 (in `make validate`, nicht
in `validate_course`); unbekannte Namen bekommen `"morph_check": false`. Nach dem Schreiben neuer Einheiten die Sätze im
Klartext rendern und Form für Form gegenlesen.

### Aufgaben: Lösungen verlassen den Server nie

`course/presenter.py` baut aus einer Aufgabe die Ansicht für den Client — Kacheln, Optionen, Paare —
und lässt die Lösung weg. Der Client schickt nur Indizes zurück, `course/checker.py` löst sie wieder
auf. Beide benutzen dieselben Presenter-Funktionen, damit die Nummerierung übereinstimmt.

Möglich wird das durch `course/shuffle.py`: das Mischen ist aus einem Seed reproduzierbar. Wer die
Reihenfolge einer Aufgabe ändert, muss also Presenter und Checker gemeinsam betrachten.

`course/service.py` verbindet Inhalt und Fortschritt und liefert die Payloads der Routen.

### Wiederholung nach Wortform, nicht nach Vokabel

SM-2 (`srs/sm2.py`) plant **einzelne Wortformen** getrennt (`де́лаю` unabhängig von `де́лает`),
gespeichert in `repositories/lexeme_srs_repo.py`. `course/review_index.py` baut daraus einen Index,
der zu jeder Form eine echte Aufgabe aus dem Kurs findet: `exact` für `choose_form` (die Form *ist*
die Lösung), `broad` für `build_sentence` (die Form kommt unter anderen vor). Deshalb muss jede neue
Einheit ihre Wörter in echten Sätzen benutzen und nicht nur in `match_pairs` — sonst findet die
Wiederholung nichts. Der Test
`test_real_content.py::test_der_index_findet_fuer_die_meisten_wortformen_eine_kontext_aufgabe`
wacht darüber (Schwelle 60 %).

### Ton

Der `tts`-Dienst hält zwei Stimmen (`PIPER_VOICE` männlich, `PIPER_VOICE_FEMALE` weiblich) und
nimmt die Rolle je Anfrage entgegen; `/api/audio?voice=m|f` reicht sie durch. Beide Namen müssen in
`backend` und `tts` übereinstimmen — ein Test in `test_compose_config.py` wacht darüber.

Das Frontend spricht nie direkt mit `tts`. Es holt Audio beim Backend, das intern erzeugen lässt und
in `audio/cache.py` zwischenspeichert (Verdrängung nach längster Nichtbenutzung, nicht nach Alter).
Stimme und Tempo gehen in den Zwischenspeicher-Schlüssel ein — `PIPER_VOICE` und
`PIPER_LENGTH_SCALE` müssen deshalb in `backend` und `tts` übereinstimmen, siehe `docker-compose.yml`.

Der Richtig-Klang (`audio/chime.ts`, über `useChime()`) erzeugt der Browser per Web Audio und
hängt nicht an Piper; der Ton-Schalter in der Kopfzeile schaltet Vorlesen und Klang gemeinsam.

Fällt der Piper-Container aus, spricht die Browserstimme; fehlt auch die, zeigen Hör-Aufgaben ihre
Textfassung. Keine Einheit wird dadurch unlösbar — dieser dreistufige Rückfall darf nicht brechen.

### Frontend

Die Startseite `views/TodayView.tsx` zeigt den Tagesplan aus `course/today.py` (`GET /api/today`):
auffrischen → neue Einheit → anwenden. Der Plan wird bei jedem Aufruf aus Zeitstempeln abgeleitet
(`review_runs`, `exercise_attempts`, `listening_runs`, …), nie gespeichert. Die Dosierungsregeln und
ihre Begründung stehen in `docs/superpowers/specs/2026-09-11-speaker-today-start-page-design.md`;
gesperrt wird nie etwas.

`courseTypes.ts` spiegelt die Backend-Payloads; Änderungen am Payload beginnen dort. `courseApi.ts`
kapselt die Aufrufe. Eine Einheit läuft in `views/UnitView.tsx` durch die Phasen Regel → neue Wörter
→ Aufgaben → Abschluss; `course/ExerciseRunner.tsx` verteilt auf die fünf Aufgabenkomponenten.
Falsch beantwortete Aufgaben wandern ans Ende der Warteschlange statt zu verschwinden.

## Arbeitsweise

Neue Einheiten immer gegen `make validate` prüfen, ein Commit je Block. Bei Änderungen am
Content-Schema wandert die Regel zusätzlich in die Prüfliste in Abschnitt 9 der Design-Spec.

Entwurfsdokumente liegen unter `docs/superpowers/specs/` und `docs/superpowers/plans/`. Das Design
des Russischkurses (`2026-09-04-speaker-russian-beginner-course-design.md`) ist die Referenz für
Stufen, Kursaufbau und Autorenregeln; bei Schema-Änderungen mitpflegen, damit es nicht veraltet.
