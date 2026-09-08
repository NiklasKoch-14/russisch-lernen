# Speaker — Russisch-Anfängerkurs: Design

Datum: 2026-09-04
Status: Entwurf zur Freigabe
Ersetzt in Teilen: `2026-07-21-speaker-language-tutor-design.md` (Phase 1, Englisch/Freitext)

## 1. Ziel

Speaker wird von „Englisch per Freitext-Chat" auf **Russisch für absolute Anfänger** umgestellt. Der
Nutzer ist deutschsprachig, hat keine russische Tastatur und (fast) keinen Wortschatz. Deshalb ist der
Lernprozess **übungsgetrieben statt chatgetrieben**: alle Eingaben erfolgen per Klick auf vorgegebene
Wortkacheln und Auswahloptionen — analog zu Duolingo, aber mit alltagstauglichen Sätzen.

Kernanforderungen aus der Anforderungsklärung:

1. **Kein Tippen auf Kyrillisch.** Jede Aufgabe ist per Klick lösbar.
2. **Schnelle Einstufung.** Ein ~2-minütiges Klick-Screening bestimmt den Startpunkt im Kurs.
3. **100 Lerneinheiten**, damit sich Inhalte nicht wiederholen.
4. **Alltagstaugliche Sätze.** „Können Sie mir helfen?" statt „Die Schlange isst einen Apfel."
5. **Wortformen als Lernschwerpunkt.** Wann heißt es `де́лаю`, wann `де́лает`, wann `де́лала` — also
   Personalendungen, Vergangenheits-Genus und Kasusendungen.
6. **Garantiert korrektes Russisch.** Lerninhalte stammen aus kuratiertem, validiertem Material, nicht
   aus dem lokalen LLM.

Unverändert gültig: Single-User ohne Login, keine API-Kosten, alles lokal via Docker/Ollama.

## 2. Warum die bestehende Architektur nicht reicht

Die Phase-1-Implementierung setzt an drei Stellen voraus, dass der Lernende die Zielsprache **frei
schreiben** kann:

- `POST /api/dialog/practice` erwartet Freitext in der Zielsprache
- `POST /api/dialog/placement/answer` stuft anhand frei formulierter Antworten ein
- `vocab_service.is_answer_correct` bewertet eine getippte Übersetzung per String-Ähnlichkeit

Für Russisch-ab-Null ist alles drei unbrauchbar. Zusätzlich ist `llama3.2:3b` auf CPU nicht
zuverlässig genug für korrekte russische Morphologie (Kasus, Aspekt, Betonung). Ein Modell, das
Lehrsätze erfindet, bringt dem Anfänger falsche Muster bei — das ist der teuerste Fehler, den diese
App machen kann.

**Konsequenz:** Lehrinhalte werden vom LLM entkoppelt. Ollama erklärt nur noch auf Deutsch, warum eine
Antwort falsch war, und führt ab Stufe 3 optionale Freidialoge. Der Kursinhalt selbst ist Daten.

## 3. Architektur

Die drei Container (`frontend`, `backend`, `ollama`) bleiben. Neu ist eine vierte Quelle: ein
versioniertes **Content-Paket** im Repository, das das Backend read-only lädt.

```
content/ru/
  lexicon.json        Wortform-Lexikon (Paradigmen, Betonung, Transliteration, Bedeutung)
  screening.json      Aufgaben der Klick-Einstufung
  primers.json        Deutsche Grundbegriffe (was ein Fall überhaupt ist)
  units/001.json … units/100.json
```

Content liegt als JSON in Git: reviewbar, diffbar, per Skript validierbar. Die SQLite-DB speichert
ausschließlich **Fortschritt**, niemals Lehrinhalt.

### 3.1 Content-Trennung Lexikon ↔ Einheit

Einheiten referenzieren **Lexikon-Formen statt roher Strings**. Ein Satz ist eine Liste von
`(lexeme_id, form_key)`-Paaren, kein Text.

Das ist die zentrale Designentscheidung, weil sie drei Dinge gleichzeitig ermöglicht:

- **Maschinelle Korrektheitsprüfung.** Ein Validator kann feststellen, ob jede benutzte Wortform im
  Lexikon existiert, Betonung trägt und im Kurs bereits eingeführt wurde.
- **Automatische Ablenker.** Der Aufgabentyp „Formauswahl" zieht falsche Optionen aus dem Paradigma
  des richtigen Wortes (`де́лаю` vs. `де́лаешь` vs. `де́лает`). Genau das gewünschte Wortform-Training,
  ohne handgepflegte Distraktorlisten.
- **SRS auf Wortform-Ebene.** Wiederholt wird nicht „die Vokabel машина", sondern gezielt die Form,
  bei der der Nutzer patzt.

### 3.2 Lexikon-Format

```json
{
  "version": 1,
  "lexemes": [
    {
      "id": "delat",
      "lemma": "де́лать",
      "pos": "verb",
      "gloss_de": "machen, tun",
      "aspect": "impf",
      "aspect_pair": "sdelat",
      "forms": {
        "inf":     {"text": "де́лать",   "translit": "délat'"},
        "prs.1sg": {"text": "де́лаю",    "translit": "délaju"},
        "prs.2sg": {"text": "де́лаешь",  "translit": "délaješ'"},
        "prs.3sg": {"text": "де́лает",   "translit": "délajet"},
        "pst.m":   {"text": "де́лал",    "translit": "délal"},
        "pst.f":   {"text": "де́лала",   "translit": "délala"}
      }
    }
  ]
}
```

Erlaubte `form_key`-Werte je Wortart (kontrolliertes Vokabular, vom Validator erzwungen):

| Wortart | Schlüssel |
|---|---|
| `verb` | `inf`, `prs.{1,2,3}{sg,pl}`, `pst.{m,f,n,pl}`, `imp.{sg,pl}`, `fut.{1,2,3}{sg,pl}` |
| `noun` | `{nom,gen,dat,acc,ins,prp}.{sg,pl}` |
| `adj` | `{nom,gen,dat,acc,ins,prp}.{m,f,n,pl}` |
| `pron` | `{nom,gen,dat,acc,ins,prp}` |
| `num` | `{nom,gen,dat,acc,ins,prp}` |
| `adv`, `prep`, `part`, `conj`, `interj` | nur `base` |
| `letter` | nur `base` |

Die Wortart `letter` trägt die Stufe-0-Inhalte: ein kyrillischer Buchstabe als Lexem, `gloss_de` ist
sein Lautwert („klingt wie *r*"). Damit braucht das Schrift-Modul kein eigenes Dateiformat und keinen
eigenen Aufgabentyp — es benutzt `match_pairs` wie alles andere.

Nur tatsächlich im Kurs benutzte Formen müssen vorhanden sein — kein vollständiges Paradigma-Pflichtprogramm.

### 3.3 Einheiten-Format

```json
{
  "id": 31,
  "stage": 2,
  "title_de": "Kaffee bestellen",
  "scenario_de": "Du stehst in einem Café und bestellst etwas zu trinken.",
  "grammar_focus": {
    "id": "prs-conj-e",
    "title_de": "Verbendungen im Präsens",
    "explanation_de": "Im Russischen zeigt die Verbendung, wer handelt …",
    "primer": "akkusativ"
  },
  "new_lexemes": ["kofe", "khotet", "pozhalujsta"],
  "exercises": [ { "id": "31-1", "type": "build_sentence", … } ]
}
```

Jede Einheit startet mit **einer kurzen deutschen Regel** (3–4 Sätze) zum Grammatik-Fokus, danach
folgen 6–10 Aufgaben. Der Erklärtext ist Pflichtfeld.

Das Feld `primer` ist optional und verweist auf einen Eintrag in `primers.json`. Ein Primer erklärt
den **deutschen** Grundbegriff — was ein Akkusativ ist, was konjugieren heißt —, nicht die russische
Regel. Der Zielnutzer hat Fälle in der Schule nie gelernt; ohne diese Vorstufe bleibt die
Einheitenregel unverständlich. Ein Primer wird **einmal geschrieben und mehrfach referenziert**: die
Einheit mit der kleinsten Id zeigt ihn aufgeklappt, jede spätere zugeklappt zum Nachschlagen.
Dieses `first_use`-Flag berechnet das Backend aus den Inhalten, es hängt nicht am Lernfortschritt.

### 3.4 Aufgabentypen

Alle vier Typen sind rein per Klick lösbar. Die Lösung verlässt den Server nie.

**`build_sentence`** — Satz aus Wortkacheln bauen.
```json
{ "id": "31-1", "type": "build_sentence",
  "prompt_de": "Ich hätte gern einen Kaffee, bitte.",
  "solution": [["ja","nom"],["khotet","prs.1sg"],["kofe","acc.sg"],["pozhalujsta","base"]],
  "distractors": [["khotet","prs.3sg"],["chaj","acc.sg"]] }
```

**`choose_form`** — Lücke mit der richtigen Wortform füllen.
```json
{ "id": "31-4", "type": "choose_form",
  "prompt_de": "Was macht sie?",
  "sentence": [["ona","nom"], "___", ["kofe","acc.sg"]],
  "answer": ["delat","prs.3sg"],
  "distractor_forms": ["prs.1sg", "prs.2sg", "pst.f"] }
```
Die Ablenker werden aus dem Paradigma desselben Lexems erzeugt — der Kern des Wortform-Trainings.

**`match_pairs`** — russische Form ↔ deutsche Bedeutung zuordnen (4–6 Paare). Ersetzt den bisherigen
getippten Vokabeltest.

**`dialog_reply`** — der Tutor sagt einen Satz, der Nutzer wählt aus drei vorgegebenen Antworten.
Jede falsche Option trägt ein `why_de`, das nach dem Klick erscheint.

## 4. Kursaufbau (100 Einheiten)

| Stufe | Einheiten | Alltagsthemen | Grammatik-Fokus |
|---|---|---|---|
| 0 Schrift & Klang | 1–4 | Lesen, Betonung | falsche Freunde `Р Н В С У Х`, `ь`, `ё` (als `letter`-Lexeme) |
| 1 Erste Sätze | 5–24 | Begrüßen, Vorstellen, Herkunft, Zahlen, Höflichkeit | Personalpronomen, Genus, fehlende Kopula |
| 2 Alltag konkret | 25–52 | Café, Einkauf, Uhrzeit, Wegbeschreibung, Wohnung, Arbeit | **Präsens-Konjugation**, Akkusativ, `в/на` + Präpositiv |
| 3 Erzählen | 53–78 | Termine, Telefon, Arzt, Reise, Verabreden | **Vergangenheit mit Genus** (`-л/-ла/-ли`), Dativ, Genitiv |
| 4 Flüssiger Alltag | 79–100 | Meinung, Probleme klären, Small Talk, Behörden | Aspektpaare, Bewegungsverben `идти/ходить`, Instrumental |

Stufe 0 bleibt bewusst klein: der Nutzer kennt die meisten Buchstaben bereits, trainiert werden nur
die trügerischen.

**Autorenregeln für Inhalte** (in der Spec verankert, teils nur menschlich prüfbar):

- Jeder Satz muss in einer realen Alltagssituation vorkommen können. Verboten sind absurde
  Lehrbuchsätze ohne Anwendungsbezug.
- Jede Einheit führt 6–10 neue Lexeme ein und benutzt sonst nur bereits eingeführte.
- Jede Einheit hat genau einen Grammatik-Fokus; mindestens 3 ihrer Aufgaben trainieren ihn.
- Ab Einheit 10 wiederholt jede Einheit mindestens 2 Lexeme aus früheren Einheiten.

## 5. Einstufung (Klick-Screening)

`screening.json` enthält 12 nach Schwierigkeit sortierte Klick-Sonden, jede mit einem
`maps_to_unit`-Wert. Ablauf:

1. Sonden werden aufsteigend gestellt (Buchstabe erkennen → Wort erkennen → Satzbedeutung → richtige
   Wortform wählen).
2. Nach **zwei aufeinanderfolgenden Fehlern** bricht das Screening ab.
3. Startpunkt = `maps_to_unit` der letzten korrekt gelösten Sonde, mindestens 1.
4. Ergebnis landet in `profile.placement_unit`; alle Einheiten davor gelten als „übersprungen" und
   bleiben jederzeit nachholbar.

Kein LLM beteiligt — deterministisch, offline, in ~2 Minuten durch.

## 6. Datenmodell (Erweiterung)

Bestehende Tabellen bleiben. Neu bzw. geändert:

```sql
-- profile: neue Spalten
ALTER TABLE profile ADD COLUMN show_transliteration INTEGER NOT NULL DEFAULT 1;
ALTER TABLE profile ADD COLUMN placement_unit INTEGER;

CREATE TABLE unit_progress (
    unit_id       INTEGER PRIMARY KEY,
    status        TEXT NOT NULL,          -- 'in_progress' | 'completed'
    correct_count INTEGER NOT NULL DEFAULT 0,
    total_count   INTEGER NOT NULL DEFAULT 0,
    completed_at  TEXT
);

CREATE TABLE exercise_attempts (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    unit_id     INTEGER NOT NULL,
    exercise_id TEXT NOT NULL,
    correct     INTEGER NOT NULL,
    answer_json TEXT NOT NULL,
    created_at  TEXT NOT NULL
);

CREATE TABLE lexeme_srs (
    lexeme_id     TEXT NOT NULL,
    form_key      TEXT NOT NULL,
    interval_days REAL NOT NULL DEFAULT 0,
    ease_factor   REAL NOT NULL DEFAULT 2.5,
    repetitions   INTEGER NOT NULL DEFAULT 0,
    due_date      TEXT NOT NULL,
    PRIMARY KEY (lexeme_id, form_key)
);

CREATE TABLE screening_results (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    answers_json   TEXT NOT NULL,
    placement_unit INTEGER NOT NULL,
    created_at     TEXT NOT NULL
);
```

`db.init_db` bekommt einen leichtgewichtigen Migrationsschritt, der fehlende `profile`-Spalten per
`PRAGMA table_info` erkennt und nachträgt. Kein Alembic — für Single-User-SQLite wäre das Overkill.

`vocab_cards` und `quiz_attempts` bleiben unangetastet im Schema, werden vom Russisch-Kurs aber nicht
mehr benutzt; der bestehende Vokabel-Flow bleibt lauffähig, bis er in einem späteren Schritt entfernt
wird.

`DEFAULT_LANGUAGE` wechselt auf `russian`, ebenso in `docker-compose.yml`.

Der Fortschritt wird ab jetzt über `placement_unit` und `unit_progress` geführt, nicht mehr über
`profile.cefr_level`. Die Spalte bleibt bestehen und wird aus der erreichten Stufe abgeleitet
(Stufe 0–1 → A1, Stufe 2 → A2, Stufe 3 → A2/B1, Stufe 4 → B1); sie dient nur noch der Anzeige im
Profil und dem Prompt des späteren Freidialogs.

## 7. API

| Methode | Pfad | Zweck |
|---|---|---|
| `GET` | `/api/course` | Stufen, Einheiten-Titel, Fortschritt, aktuelle Einheit |
| `GET` | `/api/units/{id}` | Regel + Aufgaben, Kacheln **gemischt und ohne Lösung** |
| `POST` | `/api/units/{id}/answer` | Antwort prüfen, Fortschritt und SRS aktualisieren |
| `POST` | `/api/screening/start` | Screening beginnen |
| `POST` | `/api/screening/answer` | Sonde beantworten, ggf. Einstufung abschließen |
| `GET` | `/api/review/due` | Fällige Wortformen als Klick-Aufgaben |
| `POST` | `/api/review/answer` | Wiederholungsantwort bewerten |
| `POST` | `/api/explain` | LLM-Erklärung auf Deutsch zu einem Fehler |
| `PATCH` | `/api/profile` | u. a. `show_transliteration` umschalten |

**Antwortprüfung ist serverseitig.** `GET /api/units/{id}` liefert Kacheln mit anonymen IDs in
zufälliger Reihenfolge; der Client sendet nur die gewählte Reihenfolge zurück. Damit steht die Lösung
nie im Netzwerk-Tab.

`POST /api/explain` ist der einzige LLM-Aufruf im Lernpfad. Er ist **optional**: schlägt er fehl oder
läuft in einen Timeout, zeigt die UI die statische Regel der Einheit. Kein Blockieren.

## 8. Frontend

Der bestehende Stack (Vite + React 18 + TypeScript, Tests mit Vitest/Testing-Library) bleibt. Zwei
Ergänzungen, weil aus dem Formular-Prototyp eine echte Übungs-UI wird:

- **Tailwind CSS v4** als Vite-Plugin. Das Frontend hat bisher kein Styling; Kachel-Zustände
  (ausgewählt / richtig / falsch / deaktiviert) sind mit Utility-Klassen ungleich schneller
  konsistent zu halten als mit handgeschriebenem CSS.
- **react-router** statt `useState<Tab>`. Routen `/kurs`, `/kurs/:id`, `/einstufung`, `/wiederholen`,
  `/profil` machen Reload und Zurück-Navigation innerhalb einer Einheit funktionsfähig.

Bewusst nicht eingeführt: kein State-Management-Framework (React-State plus die vorhandene
`api.ts`-Schicht genügen) und kein Drag & Drop für Wortkacheln — Antippen ist auf Mobilgeräten
robuster und barrierefreier.

Navigation: **Kurs | Wiederholen | Profil**. Der bestehende Freitext-Chat bleibt unter `/gespraech`
erhalten, wird aber erst ab Stufe 3 freigeschaltet — bis dahin fehlt schlicht das Vokabular.

Neue Komponenten:

- `CourseView` — Stufen und Einheiten als Pfad, Fortschritt pro Einheit
- `UnitView` — Regel-Kasten, dann Aufgaben-Karussell, Fortschrittsbalken, Ergebnis-Screen
- `BuildSentenceExercise`, `ChooseFormExercise`, `MatchPairsExercise`, `DialogReplyExercise`
- `ScreeningView` — die 2-Minuten-Einstufung
- `ReviewView` — fällige Wortformen, ersetzt den getippten Vokabeltest
- `RussianText` — gemeinsame Darstellung: Betonung im Kyrillischen, darunter optional die
  Transliteration, gesteuert vom Profil-Schalter

UI-Sprache bleibt Deutsch. Feedback ist sofort und nennt bei Fehlern die richtige Form samt
einzeiliger Begründung.

## 9. Content-Validierung

`backend/scripts/validate_content.py`, zusätzlich als pytest-Testfall eingebunden, sodass CI und
lokale Testläufe Inhaltsfehler fangen. Geprüfte Regeln:

1. Jede in einer Einheit referenzierte `(lexeme_id, form_key)`-Kombination existiert im Lexikon.
2. Jeder `form_key` gehört zum erlaubten Schlüsselsatz der Wortart des Lexems.
3. Jede kyrillische Form mit mehr als einer Silbe trägt genau ein Betonungszeichen (`U+0301`).
   Ausnahmen: Einsilber tragen keines, Formen mit `ё` gelten als betont (`ё` trägt im Russischen
   immer die Betonung), und Lexeme der Wortart `letter` sind ausgenommen.
4. Jede Form hat eine nichtleere Transliteration; jedes Lexem eine nichtleere deutsche Bedeutung.
5. Ein Lexem wird frühestens in der Einheit benutzt, in der es (oder eine frühere) es einführt.
6. `distractors` und `distractor_forms` enthalten nie die richtige Lösung.
7. `choose_form`-Ablenker stammen aus dem Paradigma desselben Lexems.
8. Jede Einheit hat einen nichtleeren `explanation_de`-Text und ≥ 6 Aufgaben.
9. Einheiten-IDs sind eindeutig und lückenlos von 1 bis zur höchsten vorhandenen ID. Der Validator
   fordert **nicht**, dass bereits alle 100 Einheiten existieren — Inhalte entstehen inkrementell.
   Jede vorhandene Einheit muss aber eine `stage` tragen, die zur Tabelle in Abschnitt 4 passt.
10. Jede `screening.json`-Sonde verweist auf eine existierende Einheit.
11. Jeder in `grammar_focus.primer` genannte Primer existiert in `primers.json`, und jeder
    Primer hat einen nichtleeren Titel und Text.

## 10. Testing

- **Backend (pytest):** Content-Loader, Validator (positiv und negativ), Antwortprüfung je
  Aufgabentyp, Ablenker-Erzeugung, Screening-Abbruchlogik und Einstufungs-Mapping, SRS auf
  Wortform-Ebene, Migrationsschritt, alle neuen Endpunkte mit gemocktem Ollama.
- **Frontend (vitest):** je Aufgabentyp eine Komponente (Auswahl, Absenden, Feedback),
  `RussianText`-Transliterationsschalter, `CourseView`-Fortschritt, `ScreeningView`-Ablauf.
- **Integration:** Smoke-Skript gegen den docker-compose-Stack — Screening starten, eine Einheit
  öffnen, eine Aufgabe korrekt lösen.

## 11. Umsetzungsreihenfolge

1. Content-Schema, Loader, Validator (mit ~3 Beispiel-Einheiten)
2. Datenmodell-Erweiterung und Migration
3. Antwortprüfung und SRS auf Wortform-Ebene
4. API-Endpunkte
5. Frontend: `RussianText`, vier Aufgabentypen, `UnitView`, `CourseView`
6. Screening (Backend + `ScreeningView`)
7. Inhalte auffüllen: Stufe 0 und 1 vollständig (Einheiten 1–24)
8. Restliche Einheiten 25–100 blockweise, jeder Block validiert und committet
9. `/api/explain` und Freischaltung des Freidialogs ab Stufe 3

Ab Schritt 7 ist die App benutzbar. Schritt 8 ist rein additiv: jeder Einheiten-Block wird
validiert, getestet und einzeln committet, ohne bestehende Funktionalität anzufassen.

## 12. Out of Scope

- Audio, Aussprache, TTS/STT — bleibt Phase 2 (Piper/faster-whisper)
- Mehrere Nutzer, Accounts, Login
- Andere Zielsprachen mit echten Inhalten (die Architektur bleibt sprachagnostisch, befüllt wird nur `ru`)
- Handschrift-/Tastatureingabe auf Kyrillisch
- Entfernen des alten englischen Vokabel-Flows (bleibt vorerst parallel bestehen)
