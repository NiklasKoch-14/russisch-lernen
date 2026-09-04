# Speaker — Russisch für Anfänger

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
make test        # Unit-Tests: pytest und Vitest
make test-e2e    # Playwright klickt sich durch die echte Anwendung
make smoke       # Rauchtest gegen den laufenden Stack
make validate    # Kursinhalte prüfen
```

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
