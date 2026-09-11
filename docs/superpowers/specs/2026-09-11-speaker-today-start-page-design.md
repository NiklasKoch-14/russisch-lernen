# Startseite „Heute" — Entwurf

Stand 2026-09-11. Teil 1 von 2: Tagesplan, Dosierung, Rückkehr. Teil 2 (Kann-Sätze, die erst
vergeben werden, wenn die Wiederholung bestätigt, dass es sitzt) folgt als eigene Spec.

## 1. Warum

Bisher landet man auf der Liste aller Einheiten und wählt selbst zwischen sechs Reitern. Wer jeden
Tag selbst planen muss, plant irgendwann gar nicht mehr. Die Startseite übernimmt die Rolle eines
Lehrers: Sie schlägt vor, was heute dran ist, führt durch eine sinnvolle Reihenfolge und sagt am
Ende „fertig für heute".

Beraten haben ein Russischlehrer (Didaktik) und bekannte HCI-Leitlinien:

| Entscheidung | Didaktik | HCI |
|---|---|---|
| Eine Haupthandlung statt sechs gleichwertiger Wege | „Die Startseite ist ein Lehrer, kein Menü" | Hick-Hyman-Gesetz; Material 3: ein gefüllter Knopf je Ansicht |
| Auffrischen → neue Einheit → anwenden | Aufwärmen mit Erfolg, Neues bei frischem Kopf, zum Schluss benutzen | Fogg B=MAP: die Seite ist der Anstoß, „Nur 5 Minuten" senkt die Hürde |
| Dauer statt Menge | „Nie ‚150 fällig' zeigen" | GOV.UK „Start page": sagt, wie lange es dauert; Nielsen #2 |
| Plan als Checkliste mit Stand | — | GOV.UK „Task list"; Nielsen #1 (Status sichtbar), #6 (erkennen statt erinnern) |
| Nie sperren, nur vorschlagen | — | Nielsen #3 (Kontrolle und Freiheit); Shneiderman: interne Kontrollüberzeugung |
| „Fertig für heute" | „Aufhören, solange es Spaß macht" | Shneiderman: Dialoge führen zu einem Abschluss; Peak-End-Regel |
| Keine Serien, Punkte, Prozente, Trefferquoten | erzeugen Pausenscham, belohnen Aktivität statt Können | Selbstbestimmungstheorie; Nielsen #8 (minimalistisch) |
| Neue Einheiten dosieren | eine Einheit erzeugt ~20 Wiederholungseinträge — der Berg entsteht in Woche 1 | Fehler verhüten statt heilen (Nielsen #5) |

## 2. Entscheidungen des Nutzers

- **Checkliste mit Rückkehr**: Die Startseite zeigt die Schritte mit Stand. Nach jedem Schritt geht
  es zurück, der Haken sitzt, man kann dort aufhören.
- **Dosierung wie der Lehrer**: höchstens eine neue Einheit im Plan; keine nach mehr als 7 Tagen
  Pause (am ersten Tag zurück) und keine, wenn mehr als 40 Formen anstehen. Gesperrt wird nie etwas.
- **Deckel 20 Formen** am Tag für das Auffrischen.

## 3. Datenfluss

Der Server leitet den Plan bei jedem Aufruf aus den vorhandenen Zeitstempeln ab und speichert
keinen eigenen Tageszustand — wie bei den Dorfszenen, die allein aus `(Szene, Seed)` entstehen.

`GET /api/today` liefert:

```json
{
  "greeting": "normal | welcome_back",
  "steps": [
    {"kind": "review", "status": "done | next | later", "minutes": 5,
     "title_de": "Auffrischen", "link": "/wiederholen"},
    {"kind": "unit", "status": "…", "minutes": 11, "unit_id": 46,
     "title_de": "Wo ist die Apotheke?", "detail_de": "<scenario_de>", "link": "/kurs/46"},
    {"kind": "listening | scene", "status": "…", "minutes": 3,
     "title_de": "Nach dem Weg gefragt", "detail_de": "<Ort bei Szenen>", "known": false,
     "link": "/hoeren?gespraech=21 | /dorf/kafe?szene=kafe-01"}
  ],
  "unit_skipped": "pause | backlog | all_done | null",
  "next_unit_id": 47,
  "finished": false,
  "week_days": 3,
  "offer_screening": false
}
```

Die Texte der Oberfläche (Begründungen, Knopfbeschriftungen) stehen im Frontend; der Server liefert
Daten und Inhaltstitel.

### 3.1 Aktivität und „heute"

- „Heute" ist das Datum der Server-Uhr (`dt.date.today()`), wie bei der Wiederholung. Der Container
  läuft auf UTC — der Tag wechselt also um 2 Uhr deutscher Sommerzeit. Bekannt und hingenommen.
- Ein Tag gilt als Übungstag, wenn an ihm eine dieser Zeilen entstand: `exercise_attempts`,
  `review_runs` (neu), `listening_runs`, `game_scene_runs`, `flashcard_runs`. Verglichen wird das
  Datum am Anfang des Zeitstempels.
- **Neu: `review_runs(lexeme_id, form_key, correct, answered_at)`** — beide Wiederholungsrouten
  (`/review/exercise`, `/review/answer`) schreiben je bewerteter Form eine Zeile. Bisher hielt die
  Wiederholung nicht fest, wann geübt wurde.

### 3.2 Schritt „Auffrischen"

- `reviewed` = Zeilen in `review_runs` von heute; `due` = fällige Formen jetzt.
- Kein Schritt, wenn `reviewed == 0` und `due == 0`.
- Erledigt, wenn `reviewed >= 20` oder `due == 0`.
- Minuten: `ceil(min(due, 20 - reviewed) * 25 s)`, mindestens 1.
- **Reihenfolge der fälligen Formen** (gilt für jede Wiederholungsrunde): zuerst bis zu zwei
  gefestigte Formen (Abstand ≥ 6 Tage, die längsten zuerst) zum Aufwärmen, dann die übrigen nach
  kürzestem Abstand — die zuletzt gelernten sind am meisten gefährdet. Gleichstand: Fälligkeit,
  Lexem, Form.

### 3.3 Schritt „Neue Einheit"

1. Wurde heute eine Einheit abgeschlossen (`completed_at` von heute), steht die zuletzt heute
   abgeschlossene mit Haken im Plan — auch wenn die Dosierung sonst keine vorgeschlagen hätte.
2. Sonst die nächste offene Einheit: zuerst eine angefangene (kleinste Id), sonst die kleinste
   nicht abgeschlossene ab der Einstufung (`placement_unit`, sonst 1).
3. Keine offene Einheit mehr → kein Schritt, `unit_skipped = "all_done"`.
4. **Pause**: Liegt der letzte Übungstag vor heute mehr als 7 Tage zurück → kein Schritt,
   `unit_skipped = "pause"`, `greeting = "welcome_back"`. Nur am ersten Tag zurück.
5. **Rückstand**: `due + reviewed > 40` → kein Schritt, `unit_skipped = "backlog"`. Die Summe statt
   `due` allein, damit die Entscheidung über den Tag stabil bleibt und die Einheit nicht mitten am
   Tag auftaucht, sobald man ein paar Formen abgearbeitet hat.
6. `next_unit_id` ist die Einheit aus Regel 2 (für „Noch eine Einheit"), unabhängig von 4 und 5.
7. Minuten: `ceil(Aufgaben + 0,5 × neue Wörter)`.

### 3.4 Schritt „Anwenden"

- Kandidaten: freigeschaltete Hörgespräche (`min_unit <= reached`) und Dorfszenen
  (`hint_unit <= reached`), `reached` wie beim Hören-Reiter (abgeschlossen oder eingestuft).
- Wurde heute ein Gespräch beantwortet oder eine Szene gespielt → der jüngste davon, erledigt.
- Sonst Auswahl nach: noch nie gespielt zuerst; dann Nähe der Einheit zur Bezugseinheit (heute
  abgeschlossen, sonst `reached`); dann am längsten nicht gespielt; dann Gespräch vor Szene, Id.
- Nach einer Pause (Regel 3.3.4) nur bereits Gespieltes, am längsten nicht Gespieltes zuerst —
  „ein Gespräch, das du kennst", damit der Rückkehrer merkt, dass noch alles da ist.
- Keine Kandidaten → kein Schritt.
- Minuten: Gespräch 3, Szene 4.

### 3.5 Stand und Ende

- Der erste nicht erledigte Schritt ist `next`, alle weiteren `later`.
- `finished`, wenn es Schritte gibt und alle erledigt sind.
- `week_days`: verschiedene Übungstage seit Montag dieser Woche, heute eingeschlossen.
- `offer_screening`: noch nie geübt und nicht eingestuft.

## 4. Die Seite

Route `/` und `/heute`, Reiter „Heute" an erster Stelle. Die Kopfzeile bleibt.

- **Überschrift**: „Heute" bzw. „Schön, dass du wieder da bist." Darunter „Etwa N Minuten." (Summe
  der offenen Schritte), bei `finished` stattdessen „Fertig für heute."
- **Checkliste** (`<ol>`): je Schritt Symbol (✓ erledigt, ▶ als Nächstes, ○ später), Titel, eine
  Zeile Einordnung und der Stand als Text (nicht nur als Farbe). Der nächste Schritt trägt
  `aria-current="step"`.
  - Auffrischen: „Was du schon kennst, kurz wiederholt."
  - Einheit: „Einheit 46 · Wo ist die Apotheke?" und das Szenario.
  - Gespräch: „Gespräch hören · Nach dem Weg gefragt", Hinweis „Erst hören, dann lesen." — bei
    bekannten „Kennst du schon — hör, wie viel du jetzt verstehst."
  - Szene: „Im Dorf · Bestellen bei Lena", Hinweis „Sag die Antwort laut, bevor du klickst."
- Fällt die Einheit weg, steht an ihrer Stelle ein Satz ohne Vorwurf:
  - Pause: „Heute keine neue Einheit — wir frischen erst auf."
  - Rückstand: „Heute keine neue Einheit — erst das Wiederholen, sonst wird der Stapel morgen zu hoch."
  - Alles geschafft: „Alle vorhandenen Einheiten sind geschafft — neue kommen bald."
- **Ein Hauptknopf** (gefüllt, groß): „Weiter: <nächster Schritt> · ca. N Min." Bei `finished`
  kein Hauptknopf.
- **Nebenwege** als Textlinks: „Nur 5 Minuten heute" (→ `/wiederholen`, solange Auffrischen offen
  ist und danach noch mehr käme), „Noch eine Einheit" (wenn die Einheit weggefallen oder heute schon
  erledigt ist und `next_unit_id` existiert), „Du kannst schon etwas Russisch? Einstufung · 2 Min."
  (bei `offer_screening`), „Alle Einheiten" (→ `/kurs`).
- **Wochenzeile** klein unten: „Diese Woche an 3 Tagen geübt." — erst ab einem Tag.
- Nicht auf der Seite: Anzahl fälliger Formen, Prozent, Trefferquoten, Serien, Einheitenliste.

## 5. Rückkehr

- Wiederholen: Das Rundenende bekommt „Zurück zu Heute" (Hauptknopf) und „Weiter auffrischen"
  (lädt eine neue Runde, solange etwas fällig ist).
- Einheit: Der Abschluss bekommt „Zurück zu Heute" als Hauptknopf, „Zum Kurs" daneben.
- Hören: Nach der Antwort steht „Zurück zu Heute" neben „Nächstes Gespräch". `/hoeren?gespraech=ID`
  spielt genau dieses Gespräch, sofern es freigeschaltet ist; sonst das übliche nächste.
- Dorfszene: Eine Szene braucht einen Seed, und den vergibt erst der Start. Deshalb verlinkt die
  Startseite den Ort mit `?szene=ID`; der Ort startet genau diese Szene (`scene_id` in
  `POST /game/places/{ort}/scene`) und springt hinein. Nach „Geschafft!" steht „Zurück zu Heute"
  neben „Zurück in den Raum".

## 6. Tests

- Backend: `review_runs` wird von beiden Wiederholungswegen geschrieben; Reihenfolge der fälligen
  Formen; `today.py` je Regel (erster Tag, Auffrischen offen/erledigt/Deckel, heute abgeschlossene
  Einheit, angefangene zuerst, Einstufung, Pause, Rückstand, alles geschafft, Anwenden neu/heute
  gespielt/nach Pause, Wochenzeile, `finished`); Route `/api/today`; `/listening/next?dialog_id=`.
- Frontend: `TodayView` (Checkliste, Hauptknopf, Begründungen, Fertig, Nebenwege), Rückkehr-Links.
- e2e: frische Datenbank → Startseite zeigt Einheit 1 → Hauptknopf öffnet sie.
