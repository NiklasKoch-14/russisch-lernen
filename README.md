# Russisch lernen

Selbst-gehostete Sprachlern-App mit lokalem KI-Tutor. Zielsprache ist Russisch, Bedienung auf Deutsch.
Der Lernpfad ist **klick-basiert**: Sätze werden aus vorgegebenen Wortkacheln gebaut, Wortformen aus
Optionen gewählt. Eine kyrillische Tastatur wird nie gebraucht.

Es entstehen keine API-Kosten — Textgenerierung läuft lokal über Ollama, und die Lerninhalte selbst
stammen aus einem kuratierten, maschinell geprüften Content-Paket statt aus dem Sprachmodell.

## Starten

```bash
make deploy     # baut und startet alle Container im Hintergrund
make remove     # stoppt und entfernt sie wieder, Lernfortschritt bleibt erhalten
make help       # alle Ziele
```

Ohne `make` geht es genauso mit `docker compose up -d --build` beziehungsweise `docker compose down`.

| Dienst | Port | Zweck |
|---|---|---|
| frontend | 3000 | React-Oberfläche (nginx) |
| backend | 8000 | FastAPI + SQLite |
| ollama | 11434 | lokales Sprachmodell, Default `llama3.2:3b` |
| tts | — | Piper-Sprachausgabe, nur intern erreichbar |

Der erste Start dauert länger, weil das Modell heruntergeladen wird. Ein API-Key wird nie benötigt.

## Ton

Gesprochen wird über einen eigenen Piper-Container. Er hat keinen Port nach außen — das Frontend holt
den Ton beim Backend, das ihn intern erzeugen lässt und zwischenspeichert. Gemessen: rund 100 ms beim
ersten Mal, 2 ms aus dem Zwischenspeicher.

```bash
PIPER_VOICE=ru_RU-dmitri-medium make deploy   # andere Stimme
```

Zur Auswahl stehen `ru_RU-denis-medium` (Vorgabe), `ru_RU-dmitri-medium`, `ru_RU-ruslan-medium` und `ru_RU-irina-medium`.
Tempo und Lautstärke stellen `PIPER_LENGTH_SCALE` (Vorgabe 1.15, größer heißt langsamer) und
`PIPER_VOLUME`. Ein Wechsel der Stimme entwertet den Zwischenspeicher, weil die Stimme in den Schlüssel
eingeht — die Dateien werden dann neu erzeugt, die alten fallen mit der Zeit aus dem Deckel.

`AUDIO_CACHE_MAX_MB` (Vorgabe 50) begrenzt den Platzbedarf. Verdrängt wird, was am längsten nicht
gebraucht wurde, nicht das Älteste — sonst flögen die Sätze aus Einheit 1 zuerst, obwohl die
Wiederholung sie am häufigsten braucht.

Antwortet der Piper-Container nicht, spricht die Stimme des Browsers; fehlt auch die, zeigen
Hör-Aufgaben ihre Textfassung. Keine Einheit wird dadurch unlösbar.

## Lernablauf

1. **Einstufung** (`/einstufung`) — sechs Klick-Sonden mit steigender Schwierigkeit, Abbruch nach zwei
   Fehlern in Folge. Ergebnis ist die empfohlene Starteinheit.
2. **Kurs** (`/kurs`) — Einheiten in fünf Stufen. Jede Einheit beginnt mit einer kurzen deutschen Regel
   und hat danach 6–10 Aufgaben in fünf Formaten: Satz aus Kacheln bauen, Wortform wählen, Paare
   zuordnen, Dialogantwort wählen, Gehörtes zuordnen.
3. **Wiederholen** (`/wiederholen`) — fällige Wortformen nach SM-2. Wiederholt wird nicht „die Vokabel",
   sondern die einzelne Form, bei der es hakt (`де́лаю` getrennt von `де́лает`).
4. **Dorf** (`/dorf`) — Bar, Café, Laden und Schule als anklickbare Karte; in den Räumen stehen Leute,
   die man anspricht. Ein Gespräch läuft über 2–5 Züge und **wird getippt**: kein Kachelbaukasten,
   sondern ein leeres Feld mit kyrillischer Bildschirmtastatur. Ein Schalter in der Szene stellt auf
   Kacheln zurück.

   Geprüft wird streng, aber der Fehler wird benannt. Betonungszeichen, Groß- und Kleinschreibung,
   `ё`/`е` und Satzzeichen sind egal; alles andere zählt. Weil das Lexikon jede Form kennt, kann die
   Meldung sagen, *was* stattdessen dastand — „Du hast рабо́та geschrieben — das ist Nominativ, hier
   steht Präpositiv: рабо́те." Ein bloßer Vertipper zählt nicht gegen die Wiederholungsplanung.

Der Freitext-Chat mit dem Tutor bleibt erhalten, schaltet sich aber erst ab Stufe 3 frei — davor fehlt
schlicht der Wortschatz.

## Inhalte

Der Kurs liegt als versioniertes JSON unter `content/ru/`:

- `lexicon.json` — jedes Lexem mit Formenparadigma, Betonungszeichen, Umschrift und deutscher Bedeutung
- `units/NNN.json` — je ein Alltagsszenario mit einem Grammatik-Fokus
- `screening.json` — die Sonden der Einstufung

Sätze referenzieren `(lexeme_id, form_key)`-Paare statt roher Zeichenketten. Dadurch lassen sich Inhalte
maschinell prüfen, und die Ablenker beim Aufgabentyp „Wortform wählen" entstehen automatisch aus dem
Paradigma des richtigen Wortes.

Inhalte prüfen:

```bash
cd backend && .venv/bin/python -m scripts.validate_content
```

Der Validator meldet jede Verletzung einzeln auf Deutsch — fehlende Betonung, unbekannte Wortform,
Vokabel vor ihrer Einführung benutzt, Ablenker gleich der Lösung und weitere Regeln.

## Tests

```bash
make test           # Unit-Tests: pytest und Vitest
make test-e2e       # Playwright headless — der schnelle Standardlauf
make test-e2e-show  # dasselbe im sichtbaren Browserfenster, zum Zuschauen
make test-e2e-ui    # Playwright-Oberfläche zum Zurückspulen einzelner Schritte
make smoke          # Rauchtest gegen den laufenden Stack
make validate       # Kursinhalte prüfen
```

`test-e2e-show` öffnet ein echtes Chromium-Fenster und bremst jede Aktion auf 400 ms, damit man dem
Testlauf folgen kann. Das Tempo lässt sich anpassen: `make test-e2e-show SLOW_MO=1000`. Unter WSL
braucht es dafür WSLg, also ein gesetztes `DISPLAY`.

Die Playwright-Tests unter `frontend/e2e/` starten Backend und Frontend selbst, auf eigenen Ports
(8001 und 5174) und mit einer frischen Datenbank je Lauf — ein laufender Stack wird also weder
gebraucht noch verändert. Einmalig braucht es den Browser:

```bash
cd frontend && npx playwright install chromium
```

Abgedeckt sind der Kursweg (Einheit öffnen, Regel lesen, Aufgaben lösen, Fortschritt nach Reload),
die Einstufung (Abbruch nach zwei Fehlern, Einstieg nach hinten, Speicherung im Profil) und das
Profil (Umschrift-Schalter, gesperrtes Freigespräch).

## Entwurfsdokumente

- `docs/superpowers/specs/2026-09-04-speaker-russian-beginner-course-design.md` — Design
- `docs/superpowers/plans/2026-09-04-russian-course-engine.md` — Umsetzungsplan
