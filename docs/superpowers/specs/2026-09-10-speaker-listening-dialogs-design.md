# Speaker — Hörgespräche: zwei Stimmen, blind zuhören

Erweitert `2026-09-04-speaker-russian-beginner-course-design.md` und
`2026-09-07-speaker-audio-listening-design.md`. Alles, was dort steht und hier nicht widerrufen
wird, gilt weiter.

## 1. Ziel

Alle bisherigen Hör-Aufgaben sind Einzelsätze, und der Lernende ist immer beteiligt: er bestellt,
antwortet, tippt. Was fehlt, ist das Zuhören, wenn zwei andere reden — der Normalfall in jedem Café,
jedem Laden, jedem Zugabteil. Dort versteht man nicht jedes Wort und muss trotzdem herausbekommen,
worum es geht.

Deshalb ein eigener Aufgabentyp: **zwei Figuren führen ein Gespräch, der Lernende hört zunächst nur
zu und sagt danach, worum es ging.** Nicht Wort für Wort, sondern dem Sinn nach — das ist die
Fähigkeit, die im Alltag zuerst gebraucht wird.

## 2. Entscheidungen des Nutzers (2026-09-10)

Aus dem Entwurfsgespräch, nicht still zu kippen:

- **Erster Durchlauf blind.** Beim Hören steht kein russischer Text da, nur wer gerade spricht.
  Beliebig oft wiederholbar, auch langsam. Der Text wird erst nach der Antwort aufgedeckt.
- **Eigener Tab „Hören".** Nicht in den Einheiten, nicht in der Wiederholung, nicht im Dorf. Jeder
  Aufruf zieht ein Gespräch; mit dem Fortschritt kommen längere dazu.
- **Zwei echte Stimmen.** Der `tts`-Dienst bekommt ein zweites Piper-Modell (weiblich) und nimmt die
  Stimme je Anfrage entgegen.
- **Zwanzig Gespräche zum Start**, danach wachsend.

## 3. Umfang

Neu sind: ein Inhaltsverzeichnis `content/ru/dialogs/`, ein Auswahl- und Prüfmodul im Backend, zwei
Routen, ein Tab im Frontend, ein zweites Stimmmodell im `tts`-Dienst und eine Tabelle für das
Gehörte.

**Es ändert sich kein bestehender Lerninhalt.** Die Gespräche benutzen ausschließlich Lexeme, die
der Kurs bereits eingeführt hat — sie führen selbst keine Vokabeln ein. Das ist die zentrale
Einschränkung und zugleich die Freischaltlogik (Abschnitt 6).

Daraus folgt eine Grenze, die der Nutzer kennt: **Gespräche über das Wetter sind vorerst nicht
möglich**, weil пого́да, хо́лодно, тепло́ und дождь im Lexikon fehlen. Sie kommen, sobald eine
Einheit sie einführt.

## 4. Inhaltsformat

Ein Gespräch ist eine Datei `content/ru/dialogs/NNN.json`. Sätze stehen wie überall im Kurs als
`(lexeme_id, form_key)`-Paare — nur dadurch bleiben sie maschinell prüfbar, betont, umschriftfähig
und vorlesbar.

```json
{
  "id": 13,
  "min_unit": 33,
  "title_de": "Einkauf am Freitag",
  "speakers": [
    { "name_ru": "Пётр", "name_de": "Pjotr", "voice": "m" },
    { "name_ru": "На́дя", "name_de": "Nadja", "voice": "f" }
  ],
  "lines": [
    {
      "speaker": 1,
      "tokens": [["chto", "acc"], ["ty", "nom"], ["pokupat", "prs.2sg"]],
      "translation_de": "Was kaufst du?"
    },
    {
      "speaker": 0,
      "tokens": [["ja", "nom"], ["pokupat", "prs.1sg"], ["khleb", "acc.sg"], ["i", "base"],
                 ["syr", "acc.sg"]],
      "translation_de": "Ich kaufe Brot und Käse."
    }
  ],
  "question_de": "Worum ging es?",
  "options_de": [
    "Um den Einkauf im Laden.",
    "Um die Arbeit im Büro.",
    "Um das Essen im Café.",
    "Um die Uhrzeit."
  ],
  "correct_index": 0
}
```

Zu den Feldern:

- **`min_unit`** — die Einheit, ab der das Gespräch freigeschaltet ist. Der Validator erzwingt, dass
  jedes benutzte Lexem spätestens dort eingeführt wurde.
- **`speakers`** — zwei bis drei Figuren. Namen sind Anzeigetext wie in `content/game/npcs.json` und
  bewusst **keine** Lexeme: sie sind kein Lernstoff. Es gibt keine Verbindung zum Dorf-Verzeichnis;
  dieselben Namen dürfen dort vorkommen, müssen aber nicht.
- **`voice`** — `"m"` oder `"f"`. Nicht der Modellname: welches Piper-Modell dahintersteht, gehört in
  die Konfiguration, nicht in den Inhalt.
- **`translation_de`** je Zeile — für das Transkript nach der Antwort.
- **`title_de`** — erscheint ebenfalls erst nach der Antwort; vorher verriete er die Lösung.

## 5. Ablauf

Drei Phasen in einer Ansicht.

**Phase 1 — hören.** Sichtbar sind die Namen der Sprecher und die Zeilenzahl („2 Sprecher · 5
Zeilen"), dazu Abspielen, Pause und ein Schalter für langsam. Die Zeilen werden nacheinander
abgespielt; der Chip des gerade sprechenden Namens leuchtet auf. Kein russischer Text, keine
Übersetzung. Das ganze Gespräch lässt sich beliebig oft wiederholen, einzelne Zeilen nicht — wer
nur die eine Stelle nachhört, die er ohnehin verstanden hat, übt nichts.

**Phase 2 — antworten.** Die Frage steht mit vier deutschen Optionen da. Die Reihenfolge wird aus
dem Seed gemischt (`course/shuffle.py`), damit die richtige Antwort nicht bei jedem Durchlauf an
derselben Stelle steht; der Client schickt den Index der gemischten Liste zurück, der Server löst
ihn mit derselben Funktion wieder auf. **`correct_index` verlässt den Server nicht.**

**Phase 3 — nachlesen.** Nach der Antwort erscheinen Titel, Ergebnis und das Transkript: je Zeile
Sprecher, russischer Satz, Umschrift (nach Profil-Einstellung) und deutsche Übersetzung, dazu ein
Lautsprecher-Knopf je Zeile. Darunter „nächstes Gespräch".

Der Ton der Zeilen muss dem Client schon in Phase 1 vorliegen, sonst könnte er ihn nicht abspielen —
die russischen Sätze stehen also im DOM, bevor geantwortet wird. Das ist bei `listen_meaning` heute
genauso. Zurückgehalten werden die Dinge, die die Frage beantworten würden: `correct_index`,
`title_de` und die Übersetzungen.

## 6. Auswahl und Freischaltung

`erreicht` ist die höchste Einheit mit Status `completed` (aus `progress_repo`). Wer sich hat
einstufen lassen, hat die Einheiten davor nie angefasst und kann sie trotzdem: deshalb zählt
`placement_unit - 1` gleichberechtigt mit, und `erreicht` ist das Maximum aus beidem, mindestens 0.
Ein Gespräch ist wählbar, wenn `min_unit <= erreicht`.

Gewählt wird daraus **das am längsten nicht gehörte**, bei Gleichstand nach Id — dasselbe Muster wie
`pick_scene` im Dorf, gestützt auf eine eigene Tabelle. Ein neuer Seed je Zug macht die
Optionsreihenfolge frisch. Gezählt wird erst beim Antworten, nicht beim bloßen Anhören; Wiederholen
ist damit frei.

Ist noch nichts freigeschaltet, sagt der Tab das ausdrücklich und nennt die Einheit, die das erste
Gespräch öffnet, statt eine leere Seite zu zeigen.

## 7. Ton: zwei Stimmen

**`tts`-Dienst.** `/synthesize` nimmt zusätzlich `voice: "m" | "f"` entgegen (Vorgabe `"m"`). Der
Dienst kennt zwei Modelle über `PIPER_VOICE` und `PIPER_VOICE_FEMALE` und hält beide je Prozess
geladen — geladen wird beim ersten Gebrauch, nicht beim Start. Fehlt das zweite Modell, antwortet er
**nicht** mit einem Fehler, sondern spricht mit der Vorgabestimme; `/health` nennt, welche Stimmen
wirklich da sind. Das Dockerfile lädt beide Modelle beim Bauen.

**Backend.** `/api/audio` bekommt einen optionalen Parameter `voice=m|f`. Das Backend bildet ihn auf
den konfigurierten Modellnamen ab (`PIPER_VOICE`, `PIPER_VOICE_FEMALE`) und legt diesen Namen in den
Cache-Schlüssel — der trägt die Stimme ohnehin schon. Beide Werte müssen zwischen `backend` und
`tts` übereinstimmen, wie bisher schon `PIPER_VOICE`; der Kommentar in `docker-compose.yml` wird
entsprechend erweitert.

**Rückfall.** Fällt Piper aus, spricht die Browserstimme alle Rollen — die Trennung trägt dann der
Namens-Chip. Fehlt auch sie, zeigt das Gespräch sofort sein Transkript und die Frage bleibt lösbar.
Der dreistufige Rückfall aus der Ton-Spec bleibt unangetastet.

## 8. API

```
GET  /api/listening/next
     → { dialog_id, seed, speakers[{name_ru, name_de, voice}],
         lines[{speaker, text, translit}], question_de, options_de[] }
     → { dialog_id: null, next_unit: 12 }   wenn noch nichts freigeschaltet ist

POST /api/listening/{dialog_id}/answer   { seed, option_index }
     → { correct, correct_index, title_de, translations_de[] }
```

`options_de` ist bereits gemischt; `correct_index` in der Antwort bezieht sich auf dieselbe
gemischte Liste, damit das Frontend die richtige Option markieren kann.

## 9. Datenmodell

```sql
CREATE TABLE IF NOT EXISTS listening_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dialog_id INTEGER NOT NULL,
    correct INTEGER NOT NULL,
    played_at TEXT NOT NULL
);
```

`repositories/listening_repo.py` mit `record_run` und `last_played` — Zwilling zu `game_repo`.

## 10. Content-Validierung

Die Regeln laufen im selben `validate_course`-Durchgang, damit `make validate` sie mitnimmt. Zusätzlich
zur Prüfliste in Abschnitt 9 der Kurs-Spec gilt für Gespräche:

1. Jede `(lexeme_id, form_key)`-Kombination existiert im Lexikon.
2. **Jedes benutzte Lexem wird in einer Einheit `<= min_unit` eingeführt.** Die wichtigste Regel:
   ohne sie hört der Lernende Wörter, die er nicht haben kann.
3. `min_unit` verweist auf eine existierende Einheit.
4. `speaker` jeder Zeile ist ein gültiger Index in `speakers`; es gibt zwei oder drei Sprecher, und
   jeder kommt mindestens einmal vor.
5. Mindestens drei Zeilen; jede Zeile hat eine nichtleere `translation_de`.
6. `voice` ist `"m"` oder `"f"`.
7. Mindestens drei Optionen, alle nichtleer, keine doppelt; `correct_index` liegt im Bereich.
8. Ids sind eindeutig und lückenlos ab 1 — wie bei den Einheiten, und ohne zu fordern, dass schon
   alle zwanzig da sind.
9. Keine Zeile länger als 200 Zeichen (der `tts`-Dienst nimmt 300).

## 11. Die zwanzig Gespräche

Alle Themen kommen aus dem vorhandenen Wortschatz; die Länge wächst mit der Einheit.

| # | `min_unit` | Zeilen | Worum es geht |
|---|---|---|---|
| 1 | 12 | 3 | Zwei begrüßen sich und stellen sich vor |
| 2 | 14 | 4 | Woher jemand kommt, welche Sprache er spricht |
| 3 | 16 | 3 | Wie es geht — kurzer Austausch auf der Straße |
| 4 | 18 | 4 | Über die Familie: Mann, Frau, Kinder |
| 5 | 20 | 4 | Wie alt die Kinder sind |
| 6 | 22 | 4 | Wo jemand wohnt, in welcher Stadt und Straße |
| 7 | 23 | 4 | Wer einen Hund hat und wer ein Auto |
| 8 | 25 | 4 | Was die beiden im Café trinken |
| 9 | 27 | 5 | Eine Bestellung: Suppe, Salat, Wasser |
| 10 | 29 | 5 | Wo die beiden arbeiten — Büro, Laden, Schule |
| 11 | 31 | 5 | Was etwas kostet und ob das teuer ist |
| 12 | 32 | 5 | Die Rechnung im Café, wer was nimmt |
| 13 | 33 | 5 | Einkauf: ob es Brot und Wurst gibt |
| 14 | 34 | 6 | Was man am Abend machen will — Park oder Fernseher |
| 15 | 35 | 6 | Ein Hemd aussuchen: schön, teuer, billig |
| 16 | 37 | 6 | An der Kasse: Karte oder bar, Wechselgeld |
| 17 | 39 | 5 | Wie spät es ist und ob es schon spät ist |
| 18 | 41 | 6 | Wann die beiden aufstehen und frühstücken |
| 19 | 42 | 7 | Wer wann arbeitet und wann das Wochenende beginnt |
| 20 | 44 | 8 | Ein ganzer Tag: aufstehen, Mittagessen, Abend |

Die falschen Optionen kommen möglichst aus den Themen der Nachbargespräche — so ist die Frage nur
durch Zuhören zu beantworten und nicht durch Ausschluss.

## 12. Testing

- **pytest:** Lader und Validator (positiv und negativ, je Regel aus Abschnitt 10); Auswahl
  (Eignung nach Einheit, längst-nicht-gehört, leerer Fall); Mischen und Auflösen der Optionen;
  beide Routen; `listening_repo`.
- **Echte Inhalte:** ein Test über alle ausgelieferten Gespräche — jedes benutzt nur Wörter seiner
  `min_unit`, jedes hat vier Optionen, und die Zeilenzahl wächst mit der `min_unit`, statt dass ein
  frühes Gespräch länger ist als ein spätes.
- **tts:** Synthese mit `voice=f`, unbekannte Stimme fällt auf die Vorgabe zurück, `/health` nennt
  die vorhandenen Stimmen. Die Attrappe im Test bekommt zwei Stimmen.
- **vitest:** Abspielfolge (Zeile für Zeile, Chip wechselt), kein Text vor der Antwort, Antwort
  markiert richtig und falsch, Transkript erscheint erst danach, und der Fall ohne Stimme zeigt das
  Transkript sofort.
- **Playwright:** `e2e/hoeren-dialoge.spec.ts` — Gespräch abspielen, antworten, Transkript sehen,
  nächstes Gespräch holen.

## 13. Reihenfolge der Umsetzung

1. `tts`: zweite Stimme, `voice`-Parameter, Dockerfile, `docker-compose.yml`, Tests.
2. Backend: `/api/audio?voice=`, Konfiguration, Cache-Schlüssel.
3. Frontend: `say`/`playAudio` mit `voice`.
4. Inhalt: Modelle, Lader, Validator und drei Beispielgespräche (klein, mittel, lang).
5. Backend: Auswahl, Repository, beide Routen.
6. Frontend: Tab „Hören", Player, Frage, Transkript.
7. Die restlichen siebzehn Gespräche, blockweise gegen `make validate`.
8. e2e-Lauf und ein Absatz in `CLAUDE.md` über `content/ru/dialogs/`.

## 14. Out of Scope

- **Gespräche vom Sprachmodell.** Wie beim übrigen Kurs: Inhalt ist versionierte Datei.
- **Detailfragen zusätzlich zur Sinnfrage** („Was hat sie gekauft?"). Erst wenn die Sinnfrage steht.
- **Zählung in der Wiederholungsplanung.** Hörgespräche trainieren Verstehen, keine einzelne
  Wortform; SM-2 bleibt unberührt.
- **Eigene Sprechrollen für den Lernenden.** Dafür gibt es das Dorf.
- **Wetter, Gesundheit, Verkehr** — sobald die Vokabeln in Einheiten eingeführt sind.
