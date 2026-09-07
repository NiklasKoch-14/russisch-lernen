# Speaker — Fehler-Nachlauf und Wiederholung im Kontext: Design

Datum: 2026-09-07
Status: Entwurf zur Freigabe
Ergänzt: `2026-09-04-speaker-russian-beginner-course-design.md`

## 1. Ziel

Zwei Lücken, die derselbe Gedanke schließt: **was nicht saß, muss wiederkommen — und zwar dort, wo es
gebraucht wird.**

**Fehler verschwinden heute.** Eine falsch beantwortete Aufgabe setzt den SM-2-Zähler zurück, kommt in
der Einheit aber nie wieder. `UnitView` springt zur nächsten Aufgabe und meldet am Ende „Einheit
geschafft!".

Das ist nicht nur pädagogisch dünn, sondern **schlicht falsch**: das Backend zählt eine Einheit erst
als abgeschlossen, wenn jede Aufgabe mindestens einmal richtig war (`solved >= {alle IDs}`). Wer einen
Fehler macht, sieht den Erfolgsbildschirm, während die Kursübersicht die Einheit weiter auf
„angefangen" führt. Anzeige und Datenbank widersprechen sich.

**Die Wiederholung prüft die falsche Sache.** `build_review_round` kann nur Zuordnung Form ↔ deutsche
Bedeutung. Damit übt man „`де́лает` heißt machen" — aber der Kurs dreht sich darum, *wann* es `де́лаю`
und wann `де́лает` heißt. Die Form gehört in einen Satz, nicht neben eine Vokabel.

## 2. Woher die Aufgaben kommen

Nicht aus dem Sprachmodell und nicht aus einem Generator, sondern **aus dem Kurs selbst**. Für jede
Wortform lässt sich indexieren, welche Aufgaben sie im Kontext trainieren. Das benutzt geprüfte,
validierte Inhalte wieder, statt Sätze zu erfinden, die niemand gegengelesen hat.

Gemessen im Bestand (24 Einheiten, 206 Wortformen):

| | Anzahl |
|---|---|
| Formen mit `choose_form`-Aufgabe (trifft die Form genau) | 43 |
| Formen mit irgendeiner Kontext-Aufgabe | **120** |
| Formen ohne Kontext-Aufgabe | 86, **davon 32 Buchstaben** |

Die 32 Buchstaben können keine haben: Buchstaben-Einheiten bestehen nur aus Zuordnungen, und ein
Buchstabe steht in keinem Satz. Für sie ist die Zuordnung nicht der Rückfall, sondern die richtige
Form. Ohne Buchstaben gerechnet haben **120 von 174** Formen eine Kontext-Aufgabe — gut zwei Drittel.

Der Zuordnungs-Rückfall trägt also rund ein Drittel der Wiederholung und bleibt vollwertig erhalten.

## 3. Der Index

Neu: `backend/app/course/review_index.py`.

Zwei Abbildungen, weil sie unterschiedlich gut treffen:

- **genau** — `choose_form`, deren `answer` exakt die Form ist. Dort *ist* die Form die Lösung.
- **weit** — `build_sentence`, deren `solution` die Form enthält. Sie kommt vor, aber unter anderen.

```python
ReviewIndex.exact: dict[TokenRef, list[tuple[int, str]]]   # ref -> [(unit_id, exercise_id)]
ReviewIndex.broad: dict[TokenRef, list[tuple[int, str]]]
```

Gesucht wird erst in `exact`, dann in `broad`. Der Index wird einmal je Prozess gebaut, wie der Kurs
selbst (`lru_cache` in `dependencies.py`).

**Zwei Einschränkungen bei der Auswahl:**

1. **Nur Einheiten, in denen gearbeitet wurde.** Die Kandidatenliste wird gegen `progress_repo.all_progress`
   gefiltert. Sonst schleppte die Wiederholung Vokabeln aus Einheit 22 zu jemandem, der bei 6 steht.
2. **Bei mehreren Kandidaten entscheidet ein Los** aus `shuffled_order(f"review:{today}:{ref}", n)`.
   Innerhalb eines Tages stabil, an verschiedenen Tagen verschieden — sonst käme immer dieselbe
   Aufgabe.

## 4. Die Runde

`build_review_round(conn, course, index, *, today, size=5)` liefert `{"items": [...]}`.

Ein Eintrag ist eines von zweien:

```json
{ "kind": "exercise", "unit_id": 8, "exercise_id": "8-4", "ref": "govorit:prs.1sg",
  "id": "8-4", "type": "choose_form", "prompt_de": "…", "sentence": [...], "options": [...] }

{ "kind": "pairs", "left": [...], "right": [...] }
```

Der Aufgaben-Eintrag trägt die vollständige Darstellung aus `present_exercise` — dasselbe Format, das
`UnitView` schon kennt. `unit_id` und `exercise_id` braucht der Client, um beim Antworten zu sagen,
welche Aufgabe er gelöst hat.

**Höchstens ein Zuordnungs-Eintrag je Runde.** Er sammelt alle fälligen Formen ein, für die keine
Kontext-Aufgabe gefunden wurde, und steht am Ende der Liste.

**Der Ein-Paar-Fall.** Eine Zuordnung mit einem einzigen Paar ist keine Aufgabe. Bliebe genau eine
Form ohne Kontext übrig, fiele sie Runde für Runde durch und würde nie wiederholt. Deshalb wird dann
**eine weitere fällige Form dazugenommen** — die kommt eben als Zuordnung dran, obwohl sie auch im
Kontext ginge. Findet sich keine zweite, entfällt der Zuordnungs-Eintrag und die Runde ist einen
Eintrag kürzer.

Ist nichts fällig, ist `items` leer.

## 5. Bewertung

Neu: `POST /api/review/exercise` mit `{unit_id, exercise_id, submission}`.

Er bewertet über `check_answer` und schreibt die trainierten Formen per `schedule_form` fort. Die
Antwort hat dieselbe Gestalt wie `AnswerResponse`, ohne die einheitenbezogenen Felder.

**Ausdrücklich nicht: `bump_progress` und `record_attempt`.** Beide hängen an der Einheit. Eine falsch
beantwortete Wiederholung darf eine längst abgeschlossene Einheit nicht wieder aufreißen und ihre
Statistik nicht verfälschen. Das ist die wichtigste Zusage dieses Endpunkts und bekommt einen eigenen
Test.

`POST /api/review/answer` bleibt unverändert und bedient den Zuordnungs-Eintrag.

## 6. Der Fehler-Nachlauf

Rein im Frontend. `UnitView` läuft heute mit einem Zähler `position` durch `unit.exercises`. An seine
Stelle tritt eine **Warteschlange**:

- Anfangs alle Aufgaben in ihrer Reihenfolge.
- Richtig beantwortet → fällt heraus.
- Falsch beantwortet → wandert ans Ende.
- Schlange leer → Einheit geschafft.

Das ist „bis sie richtig ist", und es macht Anzeige und Datenbank deckungsgleich: eine leere Schlange
heißt, jede Aufgabe war mindestens einmal richtig — genau die Bedingung des Backends.

**Der Fortschrittszähler** kann nicht mehr die Position sein, sonst zählte er über die Gesamtzahl
hinaus. Er wird zu *gelöste + 1 von insgesamt* und bleibt bei einer Wiederholung stehen. Das ist
ehrlich: man ist nicht weitergekommen.

**Ein Hinweis bei der Wiederholung.** Kommt eine Aufgabe erneut, steht darüber „Noch einmal — beim
letzten Mal hat es nicht gestimmt." Ohne das wirkt es wie ein Fehler der App statt wie Absicht.

Kein Backend-Anteil: Richtigkeit wird bereits erfasst, `solved_exercise_ids` liegt schon in der
Nutzlast.

## 7. Frontend der Wiederholung

`ReviewView` läuft die Einträge durch:

- `kind: "exercise"` → `ExerciseRunner` wie im Kurs, Antwort an `POST /api/review/exercise`
- `kind: "pairs"` → `MatchPairsExercise`, Antwort an `POST /api/review/answer` wie bisher

Die Ergebnisse werden gesammelt und am Ende der Runde zusammen gezeigt, wie heute auch — mit
Lautsprecher je Form.

## 8. Tests

**Index:** genau schlägt weit; nur Einheiten mit Fortschritt; das Los fällt an verschiedenen Tagen
verschieden und innerhalb eines Tages gleich.

**Runde:** Kontext-Aufgaben für Formen, die welche haben; genau ein Zuordnungs-Eintrag für den Rest;
die Auffüllregel bei einem einzelnen Übriggebliebenen; leere Runde ohne fällige Formen.

**Endpunkt:** bewertet richtig; schreibt SM-2 fort; **lässt `unit_progress` unangetastet**.

**Echter Kurs:** der Index findet für einen großen Teil der Formen etwas. Ohne diesen Test könnte eine
Content-Änderung die Kontext-Wiederholung still aushebeln.

**Frontend:** falsch beantwortete Aufgabe kommt am Ende wieder; Einheit erst geschafft, wenn alle
richtig waren; Wiederholungs-Hinweis erscheint; `ReviewView` schickt jede Eintragsart an ihren
Endpunkt.

**e2e:** eine Einheit mit absichtlich falscher Antwort, die am Ende wiederkommt.

## 9. Bewusst nicht enthalten

- **Aufgaben erzeugen.** Wo der Kurs keine Kontext-Aufgabe hergibt, bleibt es bei der Zuordnung.
  Sätze zu generieren hieße, ungeprüftes Russisch zu unterrichten.
- **Wiederholung über Einheitsgrenzen mischen** (Interleaving im Kurs selbst). Eigener Vorschlag.
- **Fehler-Nachlauf über Einheiten hinweg.** Der Nachlauf endet mit der Einheit; was darüber hinaus
  hängen bleibt, holt SM-2 in der Wiederholung.
