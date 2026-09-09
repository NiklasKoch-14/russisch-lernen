# Speaker — Tippen im Dorf: Abruf statt Wiedererkennen

Erweitert `2026-09-08-speaker-village-roleplay-design.md` und
`2026-09-04-speaker-russian-beginner-course-design.md`. Alles, was dort steht und hier nicht
widerrufen wird, gilt weiter.

## 1. Ziel

Alle fünf bestehenden Aufgabentypen und auch das Dorf sind **Wiedererkennen**: Kacheln anklicken,
Form auswählen, Paare ziehen. Wer 32 Einheiten geschafft hat, erkennt russische Sätze — im Gespräch
braucht er den Abruf aus dem Nichts. Das ist die Lücke, nicht der Stoff.

Deshalb bekommt das Dorf einen Aufgabentyp ohne Vorlage: **der Satz wird getippt.** Keine Kacheln,
keine Ablenker, nur der deutsche Auftrag und ein leeres Feld.

Ohne Spracherkennung ist Tippen der einzige Weg zum Abruf. Es ersetzt das Sprechen nicht — die
Oberfläche fordert deshalb ausdrücklich auf, den Satz erst laut zu sagen und dann zu tippen.

## 2. Entscheidungen des Nutzers (2026-09-09)

Aus dem Entwurfsgespräch, nicht still zu kippen:

- **Kyrillische Bildschirmtastatur im Layout ЙЦУКЕН.** Keine Umwandlung lateinischer Eingaben
  („privet" → приве́т). Begründung: eindeutig, und das Layout ist selbst etwas wert. Die physische
  Tastatur bleibt parallel nutzbar, falls der Nutzer ein RU-Layout einrichtet.
- **Streng geprüft, aber der Fehler wird benannt.** Nur die richtige Form zählt. Betonungszeichen,
  Groß- und Kleinschreibung, `ё`/`е` und Satzzeichen werden ignoriert. Ein reiner Tippfehler zählt
  nicht gegen die Wiederholungsplanung.
- **Ein Schalter in der Szene, Standard ist Tippen.** Alle Züge aller Szenen, keine Abstufung nach
  Zug oder Durchlauf. Der Schalter stellt jederzeit auf Kacheln zurück.
- **Zuerst das Dorf, nicht der Kurs.** Die Einheiten bleiben unverändert klickbasiert.

## 3. Umfang

Betroffen sind die Züge der Dorfszenen — heute zehn Szenen an vier Orten — sowie Presenter, Checker
und die beiden Szenenrouten.

**Es ändert sich kein Lerninhalt.** Jeder Zug trägt bereits eine `solution` als
`(lexeme_id, form_key)`-Kette, und bei den Kacheln wird schon heute die exakte Reihenfolge verlangt
(`chosen == exercise.solution`). Tippen ist also nicht strenger als der Ist-Zustand; es nimmt nur die
Vorlage weg. Alle zehn Szenen funktionieren ohne eine Zeile neuer Daten.

Unberührt bleiben: `content/ru/`, der Content-Validator und seine Prüfliste, `units/NNN.json`, die
Einstufung, die Wiederholungsansicht, das Szenenschema in `content/game/scenes/` und die Bilder.

**Nicht in dieser Fassung:** Tippen im Kurs, alternative Wortstellungen, Zeitlimit, Aufnahme der
eigenen Stimme, und die Auswertung des Fehlerbildes. Letztere kommt als eigener Schritt danach und
wird durch die getippten Antworten erst wertvoll — dann steht in der Datenbank nicht nur „falsch",
sondern *welche* Form statt der richtigen kam.

## 4. Der Aufgabentyp

```python
@dataclass(frozen=True)
class TypeSentenceExercise:
    id: str
    prompt_de: str
    solution: list[TokenRef]
```

Er tritt der Union `Exercise` bei, damit Presenter und Checker ihn typsicher behandeln. Der
**Unit-Lader erzeugt ihn nicht** — in `units/NNN.json` bleibt `type_sentence` unbekannt, und der
Validator bleibt unverändert. Gebaut wird er ausschließlich zur Laufzeit aus einem Szenenzug.

Nutzlast an den Client — die Lösung bleibt wie überall auf dem Server:

```json
{ "type": "type_sentence", "prompt_de": "Sag, dass es dir gut geht, und frag zurück.", "word_count": 3 }
```

`word_count` ist bewusst dabei: die Kachelaufgabe verrät die Satzlänge heute ohnehin, und ohne sie
rät man beim Auftrag „frag zurück", ob ein oder vier Wörter gemeint sind.

## 5. Normalisierung

`course/normalize.py`, eine Funktion, die den gesamten Toleranzbereich festlegt:

1. Unicode auf NFC bringen, dann alle Betonungszeichen U+0301 entfernen.
2. Kleinschreiben.
3. `ё` → `е`. (Russen tippen es im Alltag selbst nicht; Speaker schreibt es im Kurs, weil es beim
   Lesen hilft — beim Tippen darauf zu bestehen wäre Schikane.)
4. Alles außer kyrillischen Buchstaben, Ziffern und Leerraum entfernen — damit sind Komma, Punkt,
   Frage- und Ausrufezeichen erledigt.
5. Leerraum zusammenfassen, außen abschneiden.

Verglichen wird ausschließlich normalisiert, auf beiden Seiten. Der Bindestrich in `по-ру́сски` fällt
unter Regel 4 und verschwindet auf beiden Seiten gleich — das ist gewollt.

## 6. Rückwärts-Index über das Lexikon

`course/lexicon_index.py` baut einmal je `Course` eine Abbildung

```
normalisierter Formtext -> [(lexeme_id, form_key), ...]
```

über **alle** Formen **aller** Lexeme. Genau hier zahlt sich die Grundentscheidung des Kurses aus,
Sätze als `(lexeme_id, form_key)`-Ketten über vollständige Paradigmen zu modellieren: die
Fehlerdiagnose wird dadurch reine Datenarbeit — kein Sprachmodell erzeugt einen einzigen russischen
Buchstaben.

Mehrdeutigkeit ist der Normalfall (`рабо́те` ist Dativ und Präpositiv; `до́ма` ist Genitiv Einzahl und
Nominativ Mehrzahl), deshalb eine Liste. Der Index wird zusammen mit dem Kurs geladen und
zwischengespeichert; er ist so groß wie das Lexikon und braucht keine eigene Verwaltung.

## 7. Prüfung und Diagnose

`checker.py` bekommt `_check_type_sentence`. Die Einsendung ist `{"text": "..."}`.

Beide Seiten werden normalisiert und in Wörter zerlegt. Stimmen sie, ist die Antwort richtig. Sonst
wird die **erste** abweichende Stelle diagnostiziert — eine Meldung, nicht fünf:

| Befund | Meldung (Beispiel) | Prüfung |
|---|---|---|
| zu wenige Wörter | „Da fehlt noch etwas — gesucht sind 3 Wörter." | Länge |
| zu viele Wörter | „Ein Wort zu viel." | Länge |
| gleiche Vokabel, falsche Form | „Du hast den Nominativ geschrieben, hier steht der Präpositiv: рабо́те." | Index liefert Treffer mit demselben `lexeme_id` |
| anderes bekanntes Wort | „ко́фе heißt Kaffee — gesucht war чай." | Index liefert Treffer, anderes Lexem |
| ein Buchstabe daneben | „Fast — in рабо́те ist ein Tippfehler." | Levenshtein ≤ 1 zur erwarteten Form |
| unbekannt | „Das Wort ко́шка kommt im Kurs nicht vor." | Index leer, Levenshtein > 1 |

Reihenfolge der Prüfung: Länge, dann Index-Treffer, dann Tippfehler, dann unbekannt. Der
Tippfehler-Test steht **hinter** dem Index, sonst würde `рабо́та` gegen `рабо́те` als Tippfehler
durchgehen, obwohl es eine echte Formverwechslung ist — genau die, um die es beim Russischlernen
geht.

### Was gegen die Wiederholungsplanung zählt

`CheckResult.trained_forms` steuert, was SM-2 zu sehen bekommt.

- richtig → alle Formen der Lösung, wie bisher;
- falsche Form oder falsches Wort → alle Formen der Lösung, wie bisher (das ist ein echter Fehler);
- **Tippfehler oder unbekanntes Wort → leere Liste.** Wer `рабте` statt `рабо́те` schreibt, kann die
  Form; ihn dafür in die Wiederholung zu schicken, würde die Planung mit Handmotorik vergiften.

### Formbezeichnungen auf Deutsch

`content/formkeys.py` bekommt `form_label_de(form_key)`. Der Nutzer hat Fälle nie in der Schule
gelernt — die Bezeichnungen bleiben deshalb bei den Wörtern, die der Kurs samt Grundlagentexten
(`primers.json`) ohnehin schon benutzt, und werden bei Verben umgangssprachlich:

- Fälle: `nom` Nominativ, `gen` Genitiv, `dat` Dativ, `acc` Akkusativ, `ins` Instrumental,
  `prp` Präpositiv.
- Verbformen: `inf` „die Grundform", `prs.1sg` „die ich-Form", `prs.2sg` „die du-Form",
  `prs.3sg` „die er/sie-Form", `prs.1pl` „die wir-Form", `prs.2pl` „die ihr-Form",
  `prs.3pl` „die sie-Form", `pst.f` „die Vergangenheit weiblich", `imp.sg` „die Befehlsform".
- Zahl und Geschlecht werden nur genannt, **wenn sie sich unterscheiden**: „Nominativ" gegen
  „Präpositiv" bleibt kurz, „Akkusativ Einzahl" gegen „Akkusativ Mehrzahl" wird ausgeschrieben.
  Sonst liest man vier Wörter, von denen drei in beiden Hälften gleich sind.

## 8. Der Schalter

Neue Profilspalte `type_in_village`, Vorgabe **wahr** — dem Muster von `show_transliteration`
folgend, samt Migration in `db.py` und `PATCH /api/profile`.

Welche Aufgabenform tatsächlich **geprüft** wird, entscheidet aber nicht das Profil, sondern die
**Gestalt der Einsendung**: `{"text": …}` wird getippt geprüft, `{"tile_indices": …}` als Kacheln.
Andernfalls könnte der Schalter mitten im Zug umgelegt werden und die Prüfung passte nicht mehr zu
dem, was auf dem Bildschirm stand.

`GET /api/game/scenes/{id}/turns/{i}` nimmt dazu `?typed=true|false`. Der Client schickt, was er
gerade anzeigt; das Profil merkt sich die Einstellung nur über Sitzungen hinweg. Vertrauen ist hier
unkritisch: die getippte Ansicht verrät **weniger** als die Kacheln, nie mehr.

## 9. Oberfläche

- `CyrillicKeyboard.tsx` — drei Reihen ЙЦУКЕН, dazu Leertaste und Rücktaste. Ein Klick fügt an der
  Cursorposition ein und gibt den Fokus ans Feld zurück, damit Maus und Tastatur mischbar bleiben.
  Betonungszeichen gibt es auf der Tastatur nicht; sie werden ohnehin wegnormalisiert.
- `TypeSentenceExercise.tsx` — Auftrag, einzeiliges Feld, Wortzahl als leise Angabe, Tastatur,
  „Prüfen". Enter prüft. Nach der Prüfung wird die eigene Eingabe wortweise eingefärbt und das
  beanstandete Wort trägt die Meldung aus Abschnitt 7.
- Über dem Feld steht dauerhaft **„Erst laut sagen, dann tippen."** Kostet nichts und ist der
  einzige Hebel, der aus einer Schreibübung eine Sprechübung macht.
- Der Schalter „lieber Kacheln" sitzt in der Szene, nicht in den Einstellungen — er wird gebraucht,
  wenn *dieser* Satz zäh ist, nicht als Grundhaltung.

## 10. Testing

- `normalize`: Betonung, Groß/Klein, `ё`, Satzzeichen, Leerraum — je ein Fall.
- Rückwärts-Index: Mehrdeutigkeit (`рабо́те` liefert Dativ und Präpositiv), Vollständigkeit gegen das
  echte Lexikon.
- Checker: je ein Test pro Zeile der Tabelle in Abschnitt 7, dazu die Reihenfolge Index-vor-Tippfehler
  und die beiden `trained_forms`-Regeln.
- Presenter: die Nutzlast enthält die Lösung nicht — derselbe Wächter wie bei den anderen Typen.
- Frontend: Tastatur fügt an der Cursorposition ein; Komponente schickt den Text; Einfärbung nach
  der Antwort.
- e2e: eine Szene im Dorf tippend durchspielen, einmal falsch mit Meldung, einmal richtig; der
  Schalter stellt auf Kacheln um.

## 11. Reihenfolge der Umsetzung

Ein Commit je Block.

1. Diese Spec.
2. `normalize`, Rückwärts-Index, `form_label_de` — Bausteine mit Tests, ohne Anschluss.
3. `TypeSentenceExercise`, Presenter, Checker mit Diagnose.
4. Dorf: Profilspalte samt Migration, `?typed`, Auswahl der Aufgabenform je Zug.
5. Frontend: Tastatur, Aufgabenkomponente, Schalter, Einfärbung.
6. e2e und README.
