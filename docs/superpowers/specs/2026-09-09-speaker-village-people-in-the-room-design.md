# Speaker — Leute im Raum: Gespräche im Bild statt daneben

Erweitert `2026-09-08-speaker-village-roleplay-design.md`. Alles, was dort steht und hier nicht
widerrufen wird, gilt weiter.

## 1. Ziel

Heute zeigt ein Personen-Ort ein leeres Raumbild und darunter eine Liste von Karten mit Porträts.
Wer jemanden anspricht, landet auf einer eigenen Seite; der Raum ist weg.

Künftig stehen und sitzen die Leute **im Raum**, und man klickt sie dort an. Das Gespräch legt sich
als Karte neben die angesprochene Person, während der Raum stehen bleibt — das Vorbild ist die
Dialogansicht in Skyrim.

## 2. Entscheidungen des Nutzers (2026-09-09)

Aus dem Entwurfsgespräch, nicht still zu kippen:

- **Personen sind eine eigene Ebene über dem Raumbild**, nicht in das Raumbild hineingezeichnet.
  Begründung des Nutzers folgend: eine Person austauschen soll ein SVG kosten, nicht ein Ortsbild.
- **Das Gespräch erscheint als Karte neben der Person**, nicht als Leiste unten und nicht auf einer
  eigenen Seite. Der Raum bleibt sichtbar.
- **Nur `bar` und `kafe` werden umgebaut.** Laden und Schule behalten Bild plus Knopf — ausdrücklich
  gegen meinen Vorschlag, das ganze Dorf über Personen laufen zu lassen. Das Dorf ist damit an zwei
  von vier Orten anders bedienbar; das ist bekannt und gewollt.
- **Während eines Gesprächs ist der übrige Raum abgedunkelt und nicht anklickbar.** Ein Gespräch
  wird zu Ende geführt oder abgebrochen, nicht gewechselt.

## 3. Umfang

Betroffen sind die Orte mit `kind: "npcs"` — heute `bar` und `kafe` — und die sechs Personen dort:
`pjotr`, `nadja`, `sasha`, `oleg`, `vera`, `lena`.

Unberührt bleiben: `magazin` und `shkola` samt ihren Knöpfen, `nina` mit ihrem Brustporträt, das
Szenenschema, `presenter.py`, `checker.py`, die SM-2-Anbindung und jede Backend-Route außer der
Ortsnutzlast.

## 4. Schema: `spot` in `npcs.json`

Jede Person an einem `npcs`-Ort bekommt ein Rechteck in Anteilen des Raumbildes — dieselbe Form wie
`hotspot` bei den Orten:

```json
{
  "id": "nadja",
  "name_ru": "На́дя",
  "name_de": "Nadja",
  "place": "bar",
  "about_de": "Steht hinter der Theke und hat auf alles eine kurze Antwort.",
  "art": "npc_nadja",
  "spot": { "x": 0.34, "y": 0.22, "w": 0.13, "h": 0.46 }
}
```

**Das Rechteck ist Standort und Klickfläche zugleich.** Es gibt bewusst keine zweite Zahlenreihe für
die Klickfläche: zwei Sätze Koordinaten laufen früher oder später auseinander, und dann klickt man
neben die Person.

Die Figur wird in das Rechteck eingepasst, ohne verzerrt zu werden (`object-fit: contain`). Ob
jemand steht oder sitzt, entscheidet allein die Zeichnung — die Daten wissen davon nichts.

`spot` ist optional: Personen an Orten ohne Gespräche (Nina im Laden) brauchen keins.

## 5. Bilder

**Raumbilder** (`bar`, `kafe`) werden neu gezeichnet: leerer Raum mit klarer Bodenzone und Platz
dort, wo Leute stehen. Verhältnis bleibt 3:2.

**Figuren** (`npc_pjotr` … `npc_lena`) ersetzen die bisherigen Brustporträts: ganzkörperlich,
Hochformat, **freigestellt** — kein Hintergrundrechteck, sonst liegt ein Kasten im Raum. Nina behält
ihr Porträt, weil der Laden unverändert bleibt.

`content/game/art/PROMPTS.md` wird nachgezogen: für die sechs Leute Ganzkörper auf transparentem
Grund statt Brustbild, für die zwei Räume ausdrücklich menschenleer. Die harten Maße bekommen eine
Zeile für Figuren (Hochformat 1:2, transparent).

## 6. API

Einzige Änderung an den Nutzlasten: `place_payload` gibt je Person ihr `spot` mit, wenn eins da ist.

```json
{ "id": "nadja", "name_ru": "На́дя", "name_de": "Nadja", "about_de": "…",
  "art": "npc_nadja", "spot": { "x": 0.34, "y": 0.22, "w": 0.13, "h": 0.46 } }
```

Fehlt es, steht `"spot": null`. Routen, Szenenstart und Zug-Nutzlast bleiben, wie sie sind.

## 7. Frontend

Neue Komponente `game/PlaceStage.tsx`: Raumbild mit den Figuren darauf, positioniert aus den
Anteilen — dasselbe Muster, mit dem `VillageView` die Gebäude auf die Karte legt. Sie kennt drei
Zustände je Figur: anklickbar, abgedunkelt, hervorgehoben.

| Ansicht | benutzt `PlaceStage` |
|---|---|
| `views/PlaceView.tsx` | pur: alle Figuren anklickbar, Klick startet die Szene |
| `views/SceneView.tsx` | mit Abdunkelung, angesprochene Person hell, Dialogkarte darüber |

**Das Gespräch behält seine eigene Adresse** (`/dorf/:placeId/szene/:sceneId?seed=…`). Eine Szene
ist vollständig durch `(scene_id, seed)` bestimmt; ein Neuladen darf sie nicht verlieren.
`SceneView` lädt dafür zusätzlich den Ort, um den Raum zeichnen zu können.

**Die Karte** steht auf der Seite mit mehr Platz: Person in der linken Bildhälfte → Karte rechts,
sonst links. Sie enthält, was heute die Gesprächsseite zeigt — Satz der Person mit Hörknopf, Aufgabe,
Kacheln, „Prüfen", danach „Nochmal" oder „Weiter" — dazu ein „Zurück", das abbricht. Am Ende zeigt
dieselbe Karte das Nachwort und den Weg zurück in den Raum.

**Schmale Fenster** (unter der `sm`-Grenze): die Karte rutscht unter das Bild, der Raum bleibt
darüber sichtbar. Kein zweites Layout, nur eine andere Anordnung derselben Teile.

## 8. Rückfälle

Wie beim Ton gilt: nichts wird dadurch unbenutzbar.

1. Fehlt das Raumbild, erscheint die Liste der Leute unter dem Ortsnamen — die heutige Ansicht.
2. Fehlt die Zeichnung einer Person, bleibt ihr Rechteck als beschrifteter Knopf klickbar.
3. Fehlt einer Person das `spot` an einem `npcs`-Ort, meldet das `make validate`; zur Laufzeit
   erscheint sie in der Liste unter dem Bild statt im Raum.

## 9. Validierung

Zu den zehn Regeln der Dorf-Spec kommen drei:

11. Jede Person an einem Ort mit `kind: "npcs"` hat ein `spot`.
12. `spot`-Werte liegen zwischen 0 und 1, und `x + w` sowie `y + h` überschreiten 1 nicht.
13. Die `spot`-Rechtecke zweier Personen desselben Ortes überlappen sich nicht — sonst ist eine von
    beiden nicht mehr anklickbar.

## 10. Testing

- **Backend:** `spot` in der Ortsnutzlast (gesetzt und `null`), die drei neuen Validator-Regeln je
  einzeln, Personen ohne `spot` an Nicht-Gesprächsorten bleiben zulässig.
- **Frontend:** Figuren sitzen an den Prozentwerten aus der Nutzlast; Klick auf eine Figur startet
  die Szene; im Gespräch sind die anderen Figuren nicht anklickbar; die Karte liegt auf der freien
  Seite; ohne Raumbild erscheint die Liste.
- **e2e:** `dorf.spec.ts` spricht die Person künftig im Raum an statt in der Liste; der Durchlauf
  durch die Szene bleibt unverändert.

## 11. Umsetzungsreihenfolge

1. Schema und Validierung (Modelle, Loader, Validator, Tests)
2. Ortsnutzlast um `spot`
3. Zeichnungen: zwei leere Räume, sechs Figuren, `PROMPTS.md` nachziehen
4. `PlaceStage` und `PlaceView`
5. `SceneView` mit Karte und Abdunkelung
6. e2e und Feinjustierung der Standorte im Browser

## 12. Nicht dabei

Kein Herumlaufen, keine Animation, kein Wechsel der Person mitten im Gespräch, keine Verdeckung von
Figuren untereinander, keine Tiefenstaffelung. Laden und Schule bleiben unangetastet.
