# Speaker — Ton und Hörverstehen: Design

Datum: 2026-09-07
Status: Entwurf zur Freigabe
Ergänzt: `2026-09-04-speaker-russian-beginner-course-design.md`

## 1. Ziel

Der Kurs ist bisher vollständig stumm. Das ist die größte Lücke im Lernweg, denn Russisch ist genau
dort schwer, wo man es nicht sieht: unbetontes `о` klingt wie [a] (`молоко́` → „malakó"), `е` wird zu
[i], Endungen verschleifen. Wer nur klickt und liest, baut sich eine falsche innere Aussprache auf,
die später kaum noch zu korrigieren ist.

Diese Ausbaustufe gibt dem Kurs Ton — am Hör-Prompt, an jeder aufgelösten Lösung, in der
Vokabelliste, jeweils über ein sichtbares Lautsprecher-Symbol — und prüft Hörverstehen in drei neuen
Aufgabenformen. Der Grundsatz „nie kyrillisch
tippen" bleibt unangetastet: alle Hör-Aufgaben sind per Klick lösbar.

Nicht Teil dieser Stufe: Aussprachebewertung per Mikrofon, gesprochener Tutor-Chat.

## 2. Entscheidungen und ihre Konsequenzen

### 2.1 Sprachausgabe über die Browser-`SpeechSynthesis`

Gewählt gegenüber einem Piper-Container und gegenüber vorgerendertem Audio. Vorteil: keine zusätzliche
Infrastruktur, kein weiterer Container, keine Modell-Downloads, keine wachsenden Images.

Diese Wahl hat zwei Konsequenzen, die das übrige Design prägen:

**Der Sprechtext liegt im Klartext beim Client.** `present_exercise` hält sich bisher streng daran,
nie die Lösung mitzuschicken. Bei einer Hör-Aufgabe *ist* der gesprochene Satz aber die Lösung — er
steht damit zwangsläufig in den Netzwerkantworten. Für eine Single-User-App, in der nur der Lernende
selbst betroffen ist, wird das akzeptiert. Daraus folgt: der Server versucht gar nicht erst zu
verstecken. Er liefert `prompt_de` **und** den Sprechtext, der Client entscheidet, was er anzeigt.

**Die Stimme kann fehlen.** Unter Linux und WSL ist häufig keine `ru-RU`-Stimme installiert; dann
bleibt die Ausgabe stumm. Deshalb ist Ton eine **degradierende** Funktion, siehe 4.3. Keine Einheit
darf am fehlenden Ton scheitern.

### 2.2 Audio als Aufsatz statt als eigene Aufgabentypen

Der Unterschied zwischen „Satz nachbauen nach deutschem Text" und „Satz nachbauen nach Gehörtem" ist
allein der Prompt. Statt drei paralleler Aufgabentypen mit dreifachem Modell, Presenter, Checker,
Validator und Frontend-Komponente bekommt eine Aufgabe deshalb nur einen Schalter. `checker.py`, die
SM-2-Verbuchung der trainierten Formen und der halbe Validator gelten unverändert weiter.

Nur „Bedeutung wählen" ist wirklich neu, weil dort die Antwortoptionen deutsche Sätze sind statt
Wortkacheln.

Falls später typ-eigene Regeln auftauchen (etwa „nur einmal abspielbar"), lässt sich ein Typ jederzeit
aus dem Schalter herauslösen.

## 3. Content-Schema

### 3.1 `audio_prompt` — der Schalter

`build_sentence` und `choose_form` erhalten ein optionales Feld:

```json
{
  "id": "22-4",
  "type": "build_sentence",
  "prompt_de": "Wie alt bist du?",
  "audio_prompt": true,
  "solution": [["skolko", "base"], ["ty", "dat"], ["god", "gen.pl"]],
  "distractors": [["ty", "nom"], ["god", "nom.sg"]]
}
```

Was gesprochen wird, wird **abgeleitet**, nicht zusätzlich notiert:

- `build_sentence` → die `solution` in ihrer Reihenfolge
- `choose_form` → der `sentence` mit der `answer` in der Lücke

Damit gibt es kein zweites Feld, das aus dem Tritt geraten kann. Das Feld darf fehlen; alle
bestehenden Einheiten bleiben unverändert gültig.

`prompt_de` bleibt im Content erhalten, auch wenn es bei aktivem Ton nicht angezeigt wird — es wird
für den Textrückfall (4.3) und für die Auflösung nach der Antwort gebraucht.

### 3.2 `listen_meaning` — der neue Typ

```json
{
  "id": "25-7",
  "type": "listen_meaning",
  "prompt_de": "Hör zu. Was wird gesagt?",
  "sentence": [["ja", "nom"], ["zhit", "prs.1sg"], ["v", "base"], ["berlin", "prp.sg"]],
  "correct_index": 0,
  "options_de": [
    "Ich wohne in Berlin.",
    "Ich fahre nach Berlin.",
    "Er wohnt in Berlin."
  ]
}
```

`correct_index` bezieht sich auf die Reihenfolge in der Datei; angezeigt wird gemischt (4.1).

**Inhaltliche Regel für Autoren:** die Ablenker sind Beinahe-Treffer, die sich in genau einer Form
oder einem Wort unterscheiden. Sonst rät man an der Bedeutung vorbei, statt hinzuhören.

### 3.3 `speak_as` — Buchstaben sprechen ihren Laut, nicht ihren Namen

`speechSynthesis` liest `Р р` als Buchstabennamen („эр") vor, nicht als Laut. Das widerspricht der
Lernaussage der Buchstaben-Einheiten („klingt wie ein gerolltes r"). Eine Form im Lexikon darf deshalb
optional angeben, was stattdessen gesprochen wird:

```json
{ "id": "bu_r", "lemma": "Р р", "pos": "letter", "gloss_de": "klingt wie ein gerolltes r — nicht wie p",
  "forms": { "base": { "text": "Р р", "translit": "r", "speak_as": "ры́ба" } } }
```

Fehlt das Feld, wird `text` gesprochen. Das ist bei allen Wörtern der Normalfall.

### 3.4 Neue Validator-Regeln

Alle Meldungen auf Deutsch, einzeln pro Verletzung, wie im bestehenden Validator:

1. `audio_prompt` nur auf `build_sentence` und `choose_form` — auf anderen Typen ein Fehler.
2. `listen_meaning`: mindestens drei Optionen in `options_de`.
3. `listen_meaning`: `correct_index` liegt innerhalb von `options_de`.
4. `listen_meaning`: die Einträge in `options_de` sind paarweise verschieden und nicht leer.
5. `listen_meaning`: `sentence` ist nicht leer und enthält keine Lücken (anders als bei `choose_form`).
6. `speak_as` ist, wenn gesetzt, nicht leer.

Zusätzlich muss `_exercise_tokens` den neuen Typ kennen und die `sentence`-Token melden. Sonst greifen
weder die bestehende Prüfung „Vokabel vor ihrer Einführung benutzt" noch die SM-2-Verbuchung — ein
stiller Fehler, der sonst erst im Lernbetrieb auffiele.

## 4. Backend

| Datei | Änderung |
|---|---|
| `content/models.py` | `audio_prompt: bool = False` auf `BuildSentenceExercise` und `ChooseFormExercise`; `speak_as: str \| None = None` auf `Form`; neue Dataclass `ListenMeaningExercise`; Aufnahme in die `Exercise`-Union |
| `content/loader.py` | `audio_prompt` und `speak_as` lesen; `listen_meaning` parsen |
| `course/presenter.py` | `audio_text` liefern; `listen_meaning` darstellen |
| `course/checker.py` | `_check_listen_meaning` |
| `content/validator.py` | Regeln aus 3.4; `_exercise_tokens` erweitern |
| `db.py`, `repositories/profile_repo.py`, `api/schemas.py` | Profilspalte `audio_autoplay` |

### 4.1 Presenter

Der gesprochene Text wird **serverseitig** zusammengesetzt, nicht im Client aus Kacheln — der Client
soll nichts über russischen Satzbau wissen müssen. Für jede Aufgabe mit Ton kommt ein Feld
`audio_text` hinzu: die Wortformen mit Leerzeichen verbunden, wobei je Form `speak_as` den `text`
ersetzt, falls gesetzt.

`listen_meaning` wird dargestellt als `{id, type, prompt_de, audio_text, sentence, options_de}`, wobei
`options_de` über `shuffled_order(exercise.id, …)` gemischt wird — genau wie bei `dialog_reply`. Ohne
Mischen stünde die richtige Antwort in jeder Aufgabe an derselben Stelle. `sentence` wird als
Wortliste mitgeliefert, weil der Textrückfall (4.3) sie braucht.

### 4.2 Checker

`_check_listen_meaning` rechnet, wie `_check_dialog_reply`, vom Anzeige-Index über
`shuffled_order` auf den Original-Index zurück und vergleicht ihn mit `correct_index`. Fehlerhafte
Eingaben zählen als falsche Antwort, nie als Fehler — das gilt im bestehenden Checker durchgängig und
bleibt so.

`trained_forms` sind die Token aus `sentence`. Gehörte Formen zählen damit als Wiederholung und fließen
in SM-2 ein; das ist der halbe Sinn der Hör-Aufgaben.

`solution_text` und `solution_translit` werden aus `sentence` gerendert, `explanation_de` nennt bei
falscher Antwort die richtige deutsche Bedeutung.

### 4.3 Textrückfall bei fehlender Stimme

Weil `audio_prompt` nur ein Schalter ist, ist die Textform jeder Hör-Aufgabe bereits vorhanden. Fehlt
eine russische Stimme, zeigt der Client wieder `prompt_de` an und die Aufgabe ist die gewöhnliche
Aufgabe. `listen_meaning` zeigt statt des Tons den Satz als Text und wird zur Leseaufgabe.

Konsequenz: keine Sonderlogik in der Fortschrittsrechnung. `submit_answer` und die Prüfung auf
vollständig gelöste Einheiten bleiben unverändert.

### 4.4 Profil

Spalte `audio_autoplay INTEGER NOT NULL DEFAULT 1`, aufgenommen in die Migrationsliste in `db.py`
analog zu `show_transliteration`, durchgereicht über `profile_repo`, `schemas.py` und `PATCH /api/profile`.

Zwei Größen, die streng getrennt bleiben und **nie** miteinander verrechnet werden:

| Größe | Herkunft | Wirkt auf |
|---|---|---|
| `available` | ob eine russische Stimme existiert | den Textrückfall (4.3) |
| `audio_autoplay` | Schalter in der Kopfzeile (5.4) | ausschließlich das automatische Abspielen |

Steht `audio_autoplay` auf `false`, bleibt eine Hör-Aufgabe eine Hör-Aufgabe — es wird nur nichts von
allein abgespielt, der Lautsprecher am Prompt funktioniert weiter. Der Textrückfall greift **allein**
bei fehlender Stimme, nie wegen des Schalters. Wer die Automatik abschaltet, will Ruhe, nicht weniger
Hörtraining.

## 5. Frontend

**Neu**

- `audio/speech.ts` — Betonungszeichen entfernen, Stimme wählen, sprechen
- `audio/SpeechContext.tsx` — Provider mit `available`, `autoplay`, `speak`, `speakSlow`
- `audio/SpeakerButton.tsx` — das eine Lautsprecher-Symbol, überall wiederverwendet
- `audio/AutoplayToggle.tsx` — der Schalter in der Kopfzeile
- `course/AudioPrompt.tsx` — Abspiel-Knopf plus „langsam"
- `course/ListenMeaningExercise.tsx`

**Geändert**

- `App.tsx` — `SpeechProvider` um die App, `AutoplayToggle` in die Kopfzeile
- `course/ExerciseRunner.tsx` — neuer Fall `listen_meaning`
- `course/BuildSentenceExercise.tsx`, `course/ChooseFormExercise.tsx` — bei `audio_prompt` den
  Abspiel-Knopf statt des deutschen Prompts
- `views/UnitView.tsx` — Lautsprecher an der aufgelösten Lösung
- `views/ReviewView.tsx` — Lautsprecher je Zeile der Auflösung
- `VocabView.tsx` — Lautsprecher je Eintrag
- `ProfileView.tsx` — Hinweis bei fehlender Stimme (der Schalter selbst sitzt in der Kopfzeile)
- `courseTypes.ts` — `audio_prompt`, `audio_text`, `ListenMeaningExercise`, `audio_autoplay`

`course/Tile.tsx` bleibt **unverändert** — siehe 5.3.

### 5.1 `speech.ts`

Drei Aufgaben, bewusst ohne React-Abhängigkeit, damit sie isoliert testbar sind:

- **`stripStress(text)`** entfernt `U+0301` (kombinierendes Akut). Ein Teil der Stimmen liest es falsch
  oder buchstabiert es. `ё` bleibt erhalten — das ist ein eigener Buchstabe, kein Betonungszeichen.
- **`pickRussianVoice(voices)`** bevorzugt `lang === "ru-RU"`, sonst die erste Stimme mit `lang`, das
  mit `ru` beginnt, sonst `null`.
- **`speak(text, {rate})`** bricht laufende Ausgabe ab, dann `speechSynthesis.speak`. Tempo 0.85 als
  Standard, 0.6 für „langsam" — bei russischer Vokalreduktion ist genau das der Punkt, an dem es
  klickt.

`speechSynthesis.getVoices()` liefert beim ersten Aufruf oft eine leere Liste; das Ergebnis kommt erst
mit dem `voiceschanged`-Ereignis. Die Stimmenerkennung muss beides behandeln.

### 5.2 `SpeechContext`

Nach dem Muster von `TransliterationContext`: `available` ist `null`, solange geprüft wird, danach
`true` oder `false`. `autoplay` kommt aus dem Profil und wird wie `show_transliteration` per
`patchProfile` zurückgeschrieben.

Ist `available === false`, verschwinden alle Lautsprecher-Symbole, der Kopfzeilen-Schalter wird
ausgegraut, und alle Hör-Aufgaben fallen auf Text zurück (4.3). Im Profil steht dann ein Hinweis, wie
man eine russische Stimme nachinstalliert.

### 5.3 Lautsprecher-Symbole auf Satzebene

Ton wird **immer** über ein sichtbares Lautsprecher-Symbol ausgelöst, nie als Nebenwirkung eines
anderen Klicks. `SpeakerButton` ist dafür die einzige Komponente und sitzt an vier Stellen:

- am Hör-Prompt einer Aufgabe (zusammen mit „langsam", siehe `AudioPrompt`)
- an der aufgelösten Lösung in `UnitView`, nachdem geantwortet wurde
- an jeder Zeile der Auflösung in `ReviewView`
- an jedem Eintrag der Vokabelliste

**`Tile.tsx` bleibt unverändert.** Eine Kachel ist ein `<button>`; ein Lautsprecher-Knopf darin wäre
ein Button im Button und damit ungültiges HTML. Kacheln kommen an fünf Stellen vor, teils acht
nebeneinander — je ein zusätzliches Symbol würde sie schmaler und die Tippziele kleiner machen.
Einzelne Wörter hört man deshalb dort, wo Ruhe dafür ist: in der Auflösung und in der Vokabelliste.

Für die Buchstaben-Einheiten 1–4, die ausschließlich aus `match_pairs` bestehen, ist die Vokabelliste
zusammen mit `speak_as` (3.3) die gesamte Tonanbindung — dort gibt es keine Hör-Aufgaben.

Bewusst hingenommen: **während** einer Zuordnungsrunde in `ReviewView` gibt es keinen Ton, weil dort
nur Kacheln stehen. Er kommt in der Auflösung danach, wo jede Form einzeln nachhörbar ist.

### 5.4 Kopfzeilen-Schalter und automatisches Abspielen

In die Kopfzeile von `App.tsx` kommt neben die drei Reiter ein `AutoplayToggle` — ein Icon, das
zwischen „Automatik an" und „Automatik aus" umschaltet und den Zustand über `patchProfile` sichert.
Er gehört in die Kopfzeile und nicht ins Profil, weil man ihn situativ braucht: im Zug still lernen,
zu Hause mit Ton.

Steht die Automatik auf **an**, spielt beim Betreten einer Hör-Aufgabe der Satz einmal von allein.
Steht sie auf **aus**, passiert nichts von selbst; der Lautsprecher am Prompt bleibt bedienbar und die
Aufgabe bleibt eine Hör-Aufgabe (4.4).

Browser blockieren Sprachausgabe, bevor der Nutzer auf der Seite irgendetwas angeklickt hat. Auf der
ersten Aufgabe direkt nach dem Laden kann das automatische Abspielen deshalb stumm bleiben — der
Lautsprecher fängt das ab. Das ist bekannt und akzeptiert, keine Fehlerbehandlung nötig.

## 6. Inhalte

Alle 24 bestehenden Einheiten werden nachgerüstet, auf zwei Wegen:

- **Einheiten 1–4** (Stufe 0, Buchstaben, nur `match_pairs`): `speak_as` an allen Buchstaben-Formen im
  Lexikon. Keine neuen Aufgaben — Ton kommt über die sprechenden Kacheln.
- **Einheiten 5–24**: je Einheit ein bis zwei bestehende `build_sentence`- oder `choose_form`-Aufgaben
  bekommen `audio_prompt: true`, dazu wo inhaltlich sinnvoll eine `listen_meaning`-Aufgabe. Bestehende
  Aufgaben werden nicht neu geschrieben, nur ergänzt.

Ab Einheit 25 werden beide Formen von Anfang an eingeplant.

Nach jeder Änderung `make validate`. Der Validator sichert Struktur, Betonung und Vokabelreihenfolge —
**nicht**, ob ein Satz grammatisch stimmt und ob die Ablenker in `options_de` gute Beinahe-Treffer
sind. Das bleibt Handarbeit beim Schreiben.

## 7. Tests

Echte Sprachausgabe ist in Tests unbrauchbar, weil sie an den Stimmen der Maschine hängt. `window.speechSynthesis`
wird deshalb überall gefälscht; geprüft wird, **was** gesprochen werden sollte.

**Vitest**

- `speech.test.ts`: Betonungszeichen entfernt, `ё` bleibt, `ru-RU` wird bevorzugt, `getVoices()` erst
  leer und dann per `voiceschanged` gefüllt, laufende Ausgabe wird vor neuer abgebrochen
- `SpeakerButton` spricht den richtigen Text; `speak_as` schlägt `text`
- `AutoplayToggle` schreibt den Zustand zurück; bei `autoplay = false` spielt eine Hör-Aufgabe beim
  Betreten **nicht** von allein, ist aber weiterhin per Lautsprecher hörbar
- `ListenMeaningExercise` schickt den angeklickten Anzeige-Index
- **Der wichtigste Test:** ohne russische Stimme erscheint bei `audio_prompt` wieder der deutsche
  Prompt, und `listen_meaning` zeigt den Satz als Text — die Aufgaben bleiben lösbar

**pytest**

- Loader liest `audio_prompt`, `speak_as` und `listen_meaning`; fehlende Felder bleiben zulässig
- Presenter setzt den Sprechtext korrekt zusammen, inklusive gefüllter Lücke bei `choose_form` und
  `speak_as`-Ersetzung
- Presenter mischt `options_de`; Checker rechnet den Anzeige-Index korrekt zurück
- Checker liefert die `sentence`-Token als `trained_forms`
- Validator meldet jede Regel aus 3.4 einzeln
- `test_real_content.py` bleibt grün

**Playwright**

- ein Lauf mit gestubbtem `speechSynthesis` über `addInitScript`, der eine Hör-Aufgabe löst und die
  gesprochenen Texte prüft
- ein Lauf ohne russische Stimme, der den Textrückfall durchspielt

## 8. Abweichungen aus der Umsetzung

Drei Dinge kamen beim Bauen heraus, die beim Entwurf nicht sichtbar waren. Sie sind so umgesetzt und
gelten gegenüber den Abschnitten oben:

1. **Kein Lautsprecher in der Vokabelliste.** Abschnitt 5.3 nennt sie als vierten Ort. `VocabView.tsx`
   ist aber toter Code aus Phase 1 — nirgends importiert, keine Route, fragt getippte englische
   Übersetzungen ab. Ein Lautsprecher dort wäre unerreichbar; eine neue Vokabelliste anzulegen wäre
   eine andere Aufgabe. Stattdessen liefert die Auflösung bei `match_pairs` **einen Lautsprecher je
   Wort** — womit auch die Buchstaben-Einheiten 1–4 versorgt sind.

2. **Die Auflösung erscheint jetzt auch nach richtigen Antworten.** `UnitView` zeigte die Lösung nur
   nach Fehlern; ein Lautsprecher „an der aufgelösten Lösung" wäre also nur nach Fehlern erreichbar
   gewesen — genau verkehrt fürs Hörtraining. Ein Block bedient beide Fälle, damit der Satz nie
   doppelt dasteht.

3. **Der Kopfzeilen-Schalter ist ein `role="switch"`, nicht `aria-pressed`.** Mit `aria-pressed` kollidierte
   er mit den Wortkacheln: die e2e-Helfer finden Kacheln über genau dieses Attribut und klickten den
   Schalter statt einer Antwort. Für einen An/Aus-Schalter ist `switch` ohnehin die richtige Rolle.

Dazu eine Festlegung, die der Entwurf offen ließ: die **gesamte e2e-Suite** stubt `speechSynthesis`
und läuft standardmäßig **ohne** russische Stimme. Sonst hängt jeder Testlauf davon ab, welche Stimmen
auf der Maschine zufällig installiert sind — drei bestehende Tests fielen genau daran um.

## 9. Bewusst nicht enthalten

- **Aussprachebewertung per Mikrofon.** Bräuchte lokales ASR (whisper.cpp) und ist ein eigenes Projekt.
- **Gesprochener Tutor-Chat.** Der Chat ab Stufe 3 bleibt Text.
- **Serverseitig gerendertes Audio.** Wäre die einzige Lösung für 2.1, lohnt den Container aber nicht,
  solange nur der Lernende selbst betroffen ist.
- **Betonungszeichen ausblenden und Betonungs-Aufgaben.** Eigener Vorschlag, eigene Spec.
