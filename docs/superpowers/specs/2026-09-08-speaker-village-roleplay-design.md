# Speaker — Dorf: Rollenspiel-Ebene über dem Lernpfad

Datum: 2026-09-08
Ergänzt: `2026-09-04-speaker-russian-beginner-course-design.md` (Kurs, Einheiten, Content-Paket)

## 1. Ziel

Neben den Kurs tritt ein **Dorf**, in das der Lernende gezogen ist. Er sieht eine Karte, klickt ein
Gebäude an, spricht dort Leute an und verständigt sich auf Russisch — Antworten baut er aus
vorgegebenen Wortkacheln, wie im Kurs. Der Sprachkurs ist selbst ein Gebäude im Dorf und führt in die
nächste Lektion.

Der Kurs bleibt die Quelle des Wortschatzes. Das Dorf ist die Anwendung: dieselben Wortformen, aber
in einer Situation statt in einer Übung.

## 2. Entscheidungen des Nutzers

Am 2026-09-08 entschieden, teils gegen meine Empfehlung. Hier festgehalten, damit sie nicht später
still gekippt werden:

- **Grafik als SVG, von mir gezeichnet.** Ich kann keine Bilder erzeugen. Das Dorf und die Gebäude
  entstehen als handgezeichnete SVG. Die Bilddateien sind austauschbar, damit der Nutzer später mit
  einer anderen KI erzeugte Bilder danebenlegen kann; dafür liefere ich fertige Prompts, sobald die
  Grundsubstanz steht.
- **Lineare Gesprächszüge, kein Dialogbaum.** Eine Szene sind drei bis fünf Züge. Pro NPC liegen
  mehrere Szenen im Pool. Verzweigte Dialoge wurden verworfen: bei diesem Wortschatz ähnelten sich
  die Zweige zu stark, um den Autorenaufwand zu rechtfertigen.
- **Kein Freischalten, alles von Anfang an offen.** Ausdrücklich gegen meine Empfehlung. Szenen
  tragen einen Hinweis auf die passende Einheit, der aber nichts sperrt. Folge: der Lernende kann in
  Gespräche geraten, deren Wörter er nicht kennt. Lösbar bleibt es, weil der deutsche Auftrag und
  die Kacheln vorliegen — verstanden ist es dann nicht. Das ist bewusst in Kauf genommen.

## 3. Architektur

Das Dorf ist eine **eigene Inhaltsschicht neben dem Kurs**, kein Sonderfall einer Einheit.

Der tragende Gedanke: ein Gesprächszug referenziert dieselben `(lexeme_id, form_key)`-Paare wie eine
Kursaufgabe. Die Antwort eines Zuges *ist* eine `BuildSentenceExercise`. Damit lassen sich
`course/presenter.py` und `course/checker.py` unverändert wiederverwenden, und Kacheln, Mischen,
Vorlesen und Umschrift verhalten sich im Dorf exakt wie im Kurs — ohne zweite Implementierung, die
auseinanderlaufen könnte.

Verworfen wurden: eine Szene als Einheit mit `kind: "scene"` zu modellieren (verbiegt Stufen,
Fortschritt und SRS) und das Spiel rein im Frontend zu halten (keine Validierung, kein Fortschritt,
kein Anschluss an die Wiederholung).

Neue Module unter `backend/app/game/`:

| Modul | Aufgabe |
|---|---|
| `models.py` | `Place`, `Npc`, `Scene`, `Turn`, `Village` — eingefrorene Dataclasses wie in `content/` |
| `loader.py` | liest `content/game/`, wirft `ContentError` |
| `validator.py` | Regeln aus Abschnitt 10 |
| `scenes.py` | Szene auswählen, `shopping` aus dem Pool zusammensetzen, Zug zu einer Übung machen |
| `service.py` | Payloads der Routen, Anbindung an SRS und Fortschritt |
| `art.py` | Bilddatei zu einer Id auflösen (Raster vor SVG) |

`repositories/game_repo.py` für die gespielten Szenen. Geladen wird das Dorf einmal je Prozess über
`dependencies.py`, wie der Kurs.

## 4. Inhaltsschema

```
content/game/
  places.json       Orte samt Klickflächen auf der Karte
  npcs.json         Personen und wo sie stehen
  scenes/NNN.json   Gespräche
  art/              village.svg, bar.svg, magazin.svg, shkola.svg, kafe.svg …
  art/PROMPTS.md    Bild-Prompts für eine andere KI
```

### 4.1 `places.json`

```json
{
  "version": 1,
  "places": [
    {
      "id": "shkola",
      "name_ru": "шко́ла",
      "name_de": "Sprachkurs",
      "kind": "course",
      "art": "shkola",
      "hotspot": { "x": 0.62, "y": 0.44, "w": 0.14, "h": 0.20 }
    },
    {
      "id": "bar",
      "name_ru": "бар",
      "name_de": "Bar",
      "kind": "npcs",
      "art": "bar",
      "hotspot": { "x": 0.18, "y": 0.52, "w": 0.16, "h": 0.22 }
    }
  ]
}
```

`kind` steuert, was der Ort tut:

- `course` — kein Gespräch, sondern der Einstieg in die nächste offene Einheit. Nur `shkola`.
- `npcs` — zeigt die Personen des Ortes; eine anklicken startet eine Szene.
- `shopping` — startet direkt eine `shopping`-Szene, ohne Personenauswahl.

`hotspot` sind Anteile von 0 bis 1 auf einer Fläche im Verhältnis **16:9**. Dadurch gelten dieselben
Koordinaten für das SVG und für ein später eingesetztes Rasterbild.

### 4.2 `npcs.json`

```json
{
  "version": 1,
  "npcs": [
    {
      "id": "pjotr",
      "name_ru": "Пётр",
      "name_de": "Pjotr",
      "place": "bar",
      "about_de": "Sitzt jeden Abend am selben Platz und fragt jeden Neuen aus.",
      "art": "npc_pjotr"
    }
  ]
}
```

### 4.3 Szenen

```json
{
  "id": "bar-01",
  "kind": "dialog",
  "place": "bar",
  "npc": "pjotr",
  "title_de": "Der Mann am Tresen",
  "hint_unit": 24,
  "intro_de": "Ein älterer Mann dreht sich zu dir um.",
  "turns": [
    {
      "npc_line": [["privet", "base"], ["kak", "base"], ["dela", "nom.pl"]],
      "prompt_de": "Sag, dass es dir gut geht, und frag zurück.",
      "solution": [["khorosho", "base"], ["a", "base"], ["ty", "nom"]],
      "distractors": [["plokho", "base"], ["vy", "nom"]]
    }
  ],
  "outro_de": "Pjotr nickt und wendet sich seinem Glas zu."
}
```

`hint_unit` ist der unverbindliche Hinweis aus Abschnitt 2 — er sperrt nichts.

`npc_line` sind Token-Referenzen, keine Zeichenkette: nur so lässt sich die Zeile mit der
vorhandenen Sprachausgabe vorlesen und mit Umschrift anzeigen.

### 4.4 Der Einkaufszettel

Eine `shopping`-Szene wird nicht ausgeschrieben, sondern aus einem Pool zusammengesetzt — daher
„jedes Mal ein anderer Zettel", ohne hundert Varianten von Hand:

```json
{
  "id": "magazin-01",
  "kind": "shopping",
  "place": "magazin",
  "npc": "prodavshchitsa",
  "title_de": "Einkaufen",
  "hint_unit": 27,
  "count": 4,
  "pool": [
    ["moloko", "acc.sg"], ["ryba", "acc.sg"], ["sup", "acc.sg"],
    ["voda", "acc.sg"], ["chaj", "acc.sg"], ["pitstsa", "acc.sg"]
  ],
  "ask_template": {
    "npc_line": [["chto", "acc"], ["vy", "nom"], ["khotet", "prs.2pl"]],
    "prompt_de": "Frag nach: {item}",
    "solution": [["ja", "nom"], ["khotet", "prs.1sg"], "{item}", ["pozhalujsta", "base"]]
  },
  "closing_turn": {
    "npc_line": [["eto", "base"], ["stoit", "prs.3sg"], ["pjat", "nom"], ["evro", "gen.pl"]],
    "prompt_de": "Bezahl mit Karte und bedank dich.",
    "solution": [["karta", "nom.sg"], ["pozhalujsta", "base"]],
    "distractors": [["dengi", "nom.pl"], ["spasibo", "base"]]
  }
}
```

`{item}` ist der Platzhalter, an dem `scenes.py` die gewürfelte Ware einsetzt — in `solution` als
Token, in `prompt_de` als deutsche Bedeutung der Ware. Der Zettel wird aus einem **Seed** gezogen,
nicht aus Zufall: derselbe Seed ergibt denselben Zettel. Das macht die Szene neu ladbar und im Test
reproduzierbar.

Ablenker einer zusammengesetzten Szene sind die nicht gezogenen Waren aus dem Pool. Deshalb fordert
Regel 9 in Abschnitt 10, dass der Pool größer ist als `count`.

Die `npc_line` der Vorlage wiederholt sich in jedem Zug — die Verkäuferin fragt jedes Mal dasselbe.

## 5. Ablauf und Zustand

Szenen laufen **zustandslos**, wie Kursaufgaben. Der Server hält keine laufende Partie: eine Szene
ist vollständig bestimmt durch `(scene_id, seed)`, der Client führt den Zug-Index mit. Ein Neuladen
verliert damit nichts, solange der Seed in der URL steht.

Gespeichert wird nur, **was schon gespielt wurde** — dafür braucht es die Szenenauswahl:

```sql
CREATE TABLE IF NOT EXISTS game_scene_runs (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    scene_id   TEXT NOT NULL,
    seed       TEXT NOT NULL,
    played_at  TEXT NOT NULL
);
```

Additiv in `SCHEMA` von `db.py`, wie die übrigen Tabellen. Keine Migration nötig.

**Auswahl einer Szene:** unter den Szenen des Ortes beziehungsweise der Person gewinnt die noch nie
gespielte; gibt es keine, die am längsten zurückliegende. Das ist der Mechanismus hinter „immer
verschiedene Dialoge".

**Anbindung an die Wiederholung:** jeder beantwortete Zug meldet seine Wortformen an
`course/service.py::schedule_form`, richtig wie falsch — dieselbe SM-2-Planung wie im Kurs. Das Dorf
füttert die Wiederholung, statt daneben zu stehen.

## 6. Fehlerbehandlung

Eine falsche Antwort blockiert nie. Der NPC antwortet mit einer kurzen Verständnisfrage, die
richtige Lösung erscheint mit Umschrift und deutscher Bedeutung, und derselbe Zug wird **sofort
genau einmal** wiederholt; danach geht die Szene unabhängig vom Ausgang weiter. Anders als im Kurs
wandert der Zug nicht ans Ende — ein Gespräch, dessen dritter Satz nachgereicht wird, ergibt keinen
Sinn mehr.

Fehlt eine Bilddatei, zeigt die Karte den Ort als beschriftete Fläche — das Dorf bleibt bedienbar.
Antwortet die Sprachausgabe nicht, greift der bestehende dreistufige Rückfall.

## 7. API

Alle Routen unter `/api/game`:

| Methode | Pfad | Zweck |
|---|---|---|
| `GET` | `/village` | Orte mit Namen, Klickflächen und Bild-Id |
| `GET` | `/places/{place_id}` | Personen des Ortes, oder bei `kind: "course"` die Einheit mit der kleinsten Id, die noch nicht abgeschlossen ist |
| `POST` | `/places/{place_id}/scene` | wählt eine Szene, liefert `scene_id`, `seed`, Anzahl Züge, Intro |
| `GET` | `/scenes/{scene_id}/turns/{n}` | den Zug: NPC-Zeile und Kachelaufgabe, ohne Lösung (`seed` als Query) |
| `POST` | `/scenes/{scene_id}/turns/{n}` | Antwort prüfen; beim letzten Zug wird der Lauf verbucht |
| `GET` | `/art/{art_id}` | Bilddatei |

Die Antwort auf einen Zug hat dieselbe Gestalt wie `AnswerResponse` im Kurs, ergänzt um die Reaktion
des NPC. Lösungen verlassen den Server nie — der Client schickt Kachel-Indizes zurück, wie im Kurs.

## 8. Bild-Schnittstelle

`GET /api/game/art/{art_id}` sucht in `content/game/art/` in dieser Reihenfolge: `{id}.webp`,
`{id}.png`, `{id}.svg`. Das erste Vorhandene gewinnt.

Der Nutzer legt später erzeugte Bilder also einfach neben die SVG und sie ersetzen sie, ohne
Codeänderung. Bedingungen, die `art/PROMPTS.md` dokumentiert: Karte im Verhältnis 16:9, Gebäude im
Verhältnis 3:2, Personen quadratisch. Weicht ein Bild ab, sitzen die Klickflächen falsch.

`PROMPTS.md` enthält je Bild einen fertigen Prompt und eine gemeinsame Stilvorgabe, damit die Bilder
zueinander passen.

## 9. Frontend

Neuer Reiter **Dorf** auf `/dorf`.

`App.tsx` entscheidet künftig **pro Route über die Breite**: das Dorf bekommt die volle
Fensterbreite, Kurs, Wiederholen und Profil behalten `max-w-3xl` — lange Fließtexte über die ganze
Breite wären schlechter lesbar, nicht besser.

| Komponente | Aufgabe |
|---|---|
| `views/VillageView.tsx` | Karte, Klickflächen aus den Anteilskoordinaten |
| `views/PlaceView.tsx` | Gebäude mit seinen Personen, oder der Einstieg in die Lektion |
| `views/SceneView.tsx` | Gesprächsverlauf: NPC-Zeilen und der aktuelle Zug |
| `game/NpcLine.tsx` | eine gesprochene Zeile mit Vorlese-Knopf und Umschrift |
| `gameApi.ts`, `gameTypes.ts` | Aufrufe und Typen, getrennt von `courseApi` |

Die Kachelaufgabe selbst rendert die **vorhandene** `course/BuildSentenceExercise.tsx`. Das Dorf
bringt keine zweite Aufgabenkomponente mit.

## 10. Validierung

`make validate` prüft künftig auch das Dorf:

1. Jede `(lexeme_id, form_key)`-Kombination in einer Szene existiert im Lexikon.
2. Jeder Ort einer Szene und jeder NPC einer Szene existiert.
3. Jeder NPC steht an einem existierenden Ort.
4. Ablenker eines Zuges sind nicht Teil seiner Lösung.
5. Jede Szene hat mindestens zwei Züge, jeder Zug einen nichtleeren `prompt_de`.
6. `hotspot`-Werte liegen zwischen 0 und 1, und `x + w` sowie `y + h` überschreiten 1 nicht.
7. Klickflächen zweier Orte überlappen sich nicht.
8. Zu jedem `art`-Verweis existiert eine Datei.
9. Bei `shopping`: `count` ist kleiner als die Poolgröße, und die Lösungsvorlage enthält `{item}`
   genau einmal.
10. `hint_unit` verweist auf eine existierende Einheit.

Nicht geprüft wird — wie beim Kurs — ob ein russischer Satz grammatisch stimmt oder ob ein Gespräch
natürlich klingt. Das bleibt Handarbeit beim Schreiben.

## 11. Testing

- **pytest:** Laden, Validator positiv und negativ, Szenenauswahl (nie gespielte zuerst), Aufbau
  einer `shopping`-Szene aus dem Seed (derselbe Seed ergibt denselben Zettel), Zugprüfung, Meldung
  an das SRS, Auflösung der Bilddatei mit und ohne Rasterbild.
- **Vitest:** `VillageView` zeichnet die Klickflächen an den richtigen Anteilen und ruft beim Klick
  den Ort auf; `SceneView` zeigt die NPC-Zeile, nimmt eine Antwort entgegen und bringt nach einem
  Fehler den Zug genau einmal wieder.
- **Playwright:** ein Lauf, der aufs Dorf geht, die Bar öffnet, jemanden anspricht und eine Szene zu
  Ende bringt.

## 12. Umsetzungsreihenfolge

1. Schema, Loader, Validator, mit zwei Beispielszenen
2. `scenes.py`: Auswahl, Zusammensetzen, Zug zu Übung
3. Routen und Anbindung an SRS und Fortschritt
4. SVG für Karte und die ersten vier Gebäude
5. Frontend: Karte, Ort, Szene, volle Breite
6. Inhalte: бар mit fünf Personen, магази́н, кафе́
7. `art/PROMPTS.md`

Nach Schritt 5 ist das Dorf spielbar. Schritt 6 ist rein additiv.

## 13. Erste Orte

Vier zum Start: **шко́ла** (Sprachkurs), **кафе́** (bestellen, passt auf die Einheiten 25–32),
**магази́н** (Einkaufszettel), **бар** (fünf Personen, Small Talk).

Später naheliegend, in dieser Reihenfolge: **ры́нок** (Mengen, Preise, Handeln), **по́чта** (Paket
abholen), **апте́ка** (Symptome beschreiben), **вокза́л** (Fahrkarte, Abfahrtszeit), **дом сосе́да**
(sich und die Familie vorstellen).

## 14. Out of Scope

- Verzweigte Dialoge und wählbare Ausgänge
- Vom Sprachmodell erzeugte Gespräche — aus demselben Grund wie beim Kurs
- Freies Bewegen einer Figur; die Karte ist eine Auswahl, kein Spielfeld
- Mehrere Speicherstände oder Profile
- Tageszeit, Wetter, Inventar oder sonstige Simulation
