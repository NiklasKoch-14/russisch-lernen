# Speaker — Russisch für Anfänger

Selbst-gehostete Sprachlern-App mit lokalem KI-Tutor. Zielsprache ist Russisch, Bedienung auf Deutsch.
Der Lernpfad ist **klick-basiert**: Sätze werden aus vorgegebenen Wortkacheln gebaut, Wortformen aus
Optionen gewählt. Eine kyrillische Tastatur wird nie gebraucht.

Es entstehen keine API-Kosten — Textgenerierung läuft lokal über Ollama, und die Lerninhalte selbst
stammen aus einem kuratierten, maschinell geprüften Content-Paket statt aus dem Sprachmodell.

## Starten

```bash
docker compose up
```

| Dienst | Port | Zweck |
|---|---|---|
| frontend | 3000 | React-Oberfläche (nginx) |
| backend | 8000 | FastAPI + SQLite |
| ollama | 11434 | lokales Sprachmodell, Default `llama3.2:3b` |

Der erste Start dauert länger, weil das Modell heruntergeladen wird. Ein API-Key wird nie benötigt.

## Lernablauf

1. **Einstufung** (`/einstufung`) — sechs Klick-Sonden mit steigender Schwierigkeit, Abbruch nach zwei
   Fehlern in Folge. Ergebnis ist die empfohlene Starteinheit.
2. **Kurs** (`/kurs`) — Einheiten in fünf Stufen. Jede Einheit beginnt mit einer kurzen deutschen Regel
   und hat danach 6–10 Aufgaben in vier Formaten: Satz aus Kacheln bauen, Wortform wählen, Paare
   zuordnen, Dialogantwort wählen.
3. **Wiederholen** (`/wiederholen`) — fällige Wortformen nach SM-2. Wiederholt wird nicht „die Vokabel",
   sondern die einzelne Form, bei der es hakt (`де́лаю` getrennt von `де́лает`).

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
cd backend && .venv/bin/pytest                       # Backend
cd frontend && npm test                              # Frontend
BASE=http://localhost:8000 ./scripts/smoke_test.sh   # laufender Stack
```

## Entwurfsdokumente

- `docs/superpowers/specs/2026-09-04-speaker-russian-beginner-course-design.md` — Design
- `docs/superpowers/plans/2026-09-04-russian-course-engine.md` — Umsetzungsplan
