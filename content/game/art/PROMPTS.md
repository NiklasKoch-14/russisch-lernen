# Bild-Prompts für das Dorf

Die `.svg` in diesem Verzeichnis sind von Hand gezeichnet und tragen das Dorf, bis bessere Bilder da
sind. Diese Datei enthält die fertigen Prompts, mit denen sich die Bilder von einem Bildmodell
erzeugen lassen — englisch, weil die gängigen Modelle darauf zuverlässiger reagieren.

Ablauf: Stilblock kopieren, den gewünschten Einzelprompt anhängen, Bild erzeugen, als `.webp` unter
dem Namen aus der Überschrift hier ablegen. Mehr ist nicht zu tun — siehe „Wenn die Bilder fertig
sind" am Ende.

## Gemeinsame Stilvorgabe

Jedem Einzelprompt voranstellen, sonst passen die Bilder nicht zueinander:

```
Hand-drawn digital illustration in a warm, slightly naive storybook style. Flat colour areas with a
visible ink outline, light paper grain, no photorealism, no 3D render look. Late afternoon in early
autumn: low golden sunlight, long soft shadows, muted palette of ochre, warm grey, dusty teal and
deep red. Friendly and lived-in, never glossy or corporate. No text, no letters, no numbers, no
signage, no logos, no watermarks anywhere in the image. No frame or border.
```

Der Satz zur Schrift ist der wichtigste: Die Oberfläche legt die russischen Beschriftungen selbst
über das Bild. Kyrillisch aus einem Bildmodell ist außerdem fast immer falsch geschrieben.

## Harte Anforderungen

Ohne diese Maße sitzen die Klickflächen nicht mehr auf den Gebäuden:

| Bildart | Seitenverhältnis | Muss |
| --- | --- | --- |
| Karte (`village`) | 16:9 | vier freistehende Gebäude nebeneinander, siehe Anteile unten |
| Innenansicht (`shkola`, `kafe`, `magazin`, `bar`) | 3:2 | Blick in den Raum von der Tür aus, keine Person im Bild |
| Person in Bar/Café (`npc_pjotr`, `npc_nadja`, `npc_sasha`, `npc_oleg`, `npc_vera`, `npc_lena`) | 1:2 hoch | Ganzkörper, **freigestellt** (transparent), Füße am unteren Rand |
| Person im Laden (`npc_nina`) | 1:1 | Brustbild, frontal, Blick zum Betrachter, Kopf im oberen Drittel |

Die sechs Leute in Bar und Café stehen **im Raum**: ihr Bild wird an der Stelle eingesetzt, die
`spot` in `content/game/npcs.json` nennt. Deshalb müssen sie freigestellt sein — ein Bild mit
Hintergrund legt ein Rechteck mitten in die Gaststube. WebP kann Transparenz; wo ein Modell das
nicht liefert, ist `.png` mit Alphakanal der Ausweg. Wer sitzt, bringt seinen Stuhl mit: der Raum
zeichnet an diesen Stellen keine Möbel. Nadja ist die Ausnahme — sie steht hinter der Theke, ihr
Bild reicht nur bis zur Hüfte (Verhältnis 2:3), damit die Theke davor stehen bleibt.

Die Klickflächen der Karte stehen in `content/game/places.json` und sind Anteile der Bildbreite und
-höhe. Die Gebäude müssen von links nach rechts in dieser Reihenfolge und an diesen Stellen stehen:

| Gebäude | waagerecht | senkrecht |
| --- | --- | --- |
| Schule (`шко́ла`) | 8 % bis 26 % | 30 % bis 60 % |
| Café (`кафе́`) | 30 % bis 48 % | 34 % bis 62 % |
| Laden (`магази́н`) | 52 % bis 70 % | 32 % bis 62 % |
| Bar (`бар`) | 74 % bis 92 % | 36 % bis 64 % |

Also: oberes Viertel Himmel, unteres Drittel Straße, die Fassaden dazwischen. Wer die Karte anders
aufbaut, muss `places.json` mit ändern — `make validate` prüft nur, dass sich die Flächen nicht
überlappen, nicht, ob unter ihnen ein Gebäude liegt.

## Die Prompts

### `village` — die Dorfkarte

```
A small Russian village street seen straight on from across the road, four separate one- and
two-storey buildings standing side by side with narrow gaps between them. From left to right: a pale
yellow plastered schoolhouse with tall windows and a small stair to the door; a mint-green wooden
cafe with a striped awning and two tables outside; a squat brick corner shop with a wide display
window and crates by the entrance; a dark red brick bar with small deep-set windows and a lamp over
the door. Empty asphalt road with puddles across the bottom third, a strip of blue sky and a few
birds across the top quarter, birches and a wooden fence in the gaps between the buildings.
```

### `shkola` — Klassenzimmer

```
Interior of a small village classroom seen from the doorway: six worn wooden desks in two rows
facing a dark green chalkboard, a globe and stacked books on the teacher's desk, tall windows on the
left letting in low afternoon sun, a potted plant on the sill, coats on hooks by the door. Empty of
people, chalk dust in the light.
```

### `kafe` — Gaststube im Café

```
Interior of a tiny village cafe seen from the doorway: four round tables with mismatched chairs, a
wooden counter with a chrome coffee machine and a glass cake dome, patterned curtains, a shelf of
cups behind the counter, warm lamps hanging low over the tables. Completely empty of people — the staff is drawn
separately and placed on top. One cup left on a table.
```

### `magazin` — Verkaufsraum

```
Interior of a small village grocery shop seen from the doorway: two narrow aisles of wooden shelves
with tins, jars, bread and bottles, a chest freezer along the wall, a counter with an old till and a
set of scales, crates of apples and potatoes on the floor. Empty of people, daylight from the shop
window on the left.
```

### `bar` — Gaststube in der Bar

```
Interior of a small village bar in the evening seen from the doorway: a long dark wooden counter
with four stools, bottles and glasses on a shelf behind it, two booths with red upholstery along the
right wall, a beer tap, low warm lamps and deep shadows in the corners. Completely empty of people and empty
of bar stools at the front — guests and their stools are drawn separately and placed on top. One
glass standing on the counter.
```

### `npc_pjotr` — Pjotr, Bar

```
Full-body portrait of a Russian man in his late sixties sitting on a plain wooden bar stool, both
hands resting on an invisible table, knees towards the viewer. Weathered friendly face, deep
forehead lines, thick grey moustache, thinning grey hair under a dark flat cap, worn grey-brown
jacket over a light shirt, dark trousers, heavy shoes. Calm, curious expression. Cut out on a fully
transparent background, no floor, no shadow, no scenery.
```

### `npc_nadja` — Nadja, Bar (die Wirtin)

```
Half-body portrait of a Russian woman in her forties, cropped at the hips, standing and leaning
slightly forward as if behind a counter. Auburn hair in a tight bun, gold hoop earrings, teal blouse
under a light apron, alert eyes, short friendly half-smile, one hand wiping with a cloth. Cut out on
a fully transparent background, no counter, no floor, no shadow.
```

### `npc_sasha` — Sascha, Bar (jung, redet schnell)

```
Full-body portrait of a Russian man in his early twenties standing, one hand raised mid-gesture as
if explaining something, mouth open mid-sentence. Messy dark hair, wide open eyes, raised eyebrows,
blue hoodie with loose strings, jeans, dark sneakers. Energetic and talkative. Cut out on a fully
transparent background, no floor, no shadow, no scenery.
```

### `npc_oleg` — Oleg, Bar (wortkarg)

```
Full-body portrait of a broad-shouldered Russian man in his fifties sitting on a plain wooden bar
stool, knees apart, a glass of beer in one hand. Square face, full dark beard, narrow eyes under
heavy brows, dark red knitted beanie, olive work jacket over a grey sweater, dark trousers, work
boots. Silent, unbothered expression. Cut out on a fully transparent background, no floor, no
shadow, no scenery.
```

### `npc_vera` — Vera, Bar (fragt nach der Familie)

```
Full-body portrait of a Russian woman in her sixties sitting on a simple wooden chair, leaning in
with a broad, genuinely interested smile, a small glass in one hand. Round glasses, warm laugh
lines, blue patterned headscarf tied under the chin, dark red floral blouse, dark skirt. Cut out on
a fully transparent background, no floor, no shadow, no scenery.
```

### `npc_lena` — Lena, Café (Kellnerin)

```
Full-body portrait of a Russian woman in her thirties standing, balancing a small wooden tray with
one cup on her raised hand. Dark blonde hair in a ponytail, white shirt with a black apron, dark
trousers, patient attentive smile, head slightly tilted. Cut out on a fully transparent background,
no floor, no shadow, no scenery.
```

### `npc_nina` — Nina, Laden

```
Portrait of a Russian woman in her sixties behind a shop counter: short grey permed hair, reading
glasses low on the nose, dark blue shop coat over a knitted cardigan, hands resting on the counter.
Knowing, no-nonsense but not unfriendly expression. Blurred shelves of tins and jars behind her.
```

## Wenn die Bilder fertig sind

1. Jedes Bild als `.webp` unter dem Namen aus der jeweiligen Überschrift in dieses Verzeichnis
   legen: `village.webp`, `bar.webp`, `npc_pjotr.webp` und so weiter.
2. `make validate` laufen lassen. Meldet es nichts, ist alles am Platz.
3. Fertig — keine Codeänderung nötig. Das Backend sucht je Bild-Id in der Reihenfolge `.webp`,
   `.png`, `.svg` und nimmt die erste Datei, die es findet (`backend/app/game/art.py`).

Die `.svg` bleiben liegen. Sie sind der Rückfall für jedes Bild, das noch fehlt oder das man wieder
entfernt — und sie kosten nichts, weil sie nur ausgeliefert werden, wenn kein Rasterbild da ist.
