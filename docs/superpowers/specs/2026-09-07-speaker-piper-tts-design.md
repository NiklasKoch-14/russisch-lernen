# Speaker — Sprachausgabe über Piper: Design

Datum: 2026-09-07
Status: Entwurf zur Freigabe
Ergänzt: `2026-09-07-speaker-audio-listening-design.md`

## 1. Ziel

Die Sprachausgabe läuft bisher über die Stimmen des Browsers. Auf dem Rechner des Nutzers stehen
dafür genau zwei zur Wahl, und beide sind unbrauchbar:

- **`Microsoft Dmitry Online (Natural)`** klingt gut, schickt aber jeden Satz an einen Microsoft-Server.
  Der Ton setzt spürbar verzögert ein und stockt mitten im Satz.
- **`Microsoft Irina Desktop`** ist sofort da, aber leise, blechern und verschluckt den Anlaut kurzer
  Wörter — `дом` war kaum zu verstehen.

Zwischen beiden gibt es keinen guten Kompromiss, und die Auswahl hängt zudem davon ab, welche Stimmen
auf einem Windows zufällig installiert sind. Ein eigener Dienst löst das: gleiche Stimme auf jedem
Rechner, kein Netzweg, Lautstärke und Tempo einstellbar.

Zusätzlich wird damit möglich, was der Nutzer ursprünglich wollte und was die Browser-Schnittstelle
prinzipiell nicht hergibt: **den Ton vorab zu holen.** `SpeechSynthesis` gibt das erzeugte Audio nie
heraus; Piper liefert Dateien, die sich vorladen lassen.

## 2. Was Piper nicht löst

**Die Betonung wird nicht besser.** Das ist die wichtigste Einschränkung und stand am Anfang der
Überlegung als erhoffter Hauptgewinn.

Der Content trägt Betonungszeichen (`U+0301`), und die Hoffnung war, dass ein serverseitiger Dienst
sie auswertet. Piper phonemisiert über espeak-ng, dessen Russisch-Modul diese Zeichen ignoriert; ein
Vorschlag zur Unterstützung wurde im espeak-ng-Projekt abgelehnt, weil er bestehende Anwendungen zu
stark verändert hätte. Es existiert eine Gemeinschaftsabspaltung der espeak-Daten, die es nachrüstet
— ein zusätzliches, unbetreutes Glied in der Kette, das hier bewusst **nicht** verwendet wird.

Piper rät die Betonung also aus seinem Wörterbuch, genau wie die Microsoft-Stimmen es tun. Bei
beweglicher Betonung (`го́род` → `города́`) kann das falsch sein. Der Nutzer hat das Vorhaben in
Kenntnis dieser Einschränkung freigegeben.

**Piper ist im Ursprungsprojekt seit Oktober 2025 archiviert.** Die Weiterentwicklung liegt bei der
Open Home Foundation (`OHF-Voice/piper1-gpl`), das pip-Paket heißt weiterhin `piper-tts`.

## 3. Architektur

```
Frontend ──HTTP──> Backend ──intern──> tts (Piper)
                      │
                      └── Cache unter /data/audio im vorhandenen backend_data-Volume
```

Der `tts`-Dienst bekommt **keinen `ports`-Eintrag** und ist damit nur im Docker-Netz erreichbar. Das
Frontend spricht ausschließlich das Backend an.

Der Grund gegen einen direkten Zugriff des Frontends auf Piper: es bräuchte einen weiteren offenen
Port, eine CORS-Freigabe und ein zweites Volume für den Zwischenspeicher. So bleibt es bei einer
Adresse und einem Volume.

### 3.1 Der `tts`-Dienst

Neues Verzeichnis `tts/` mit `Dockerfile`, `requirements.txt` und `app.py`.

```
POST /synthesize   {"text": "я говорю по-русски"}  →  audio/wav
GET  /health       →  {"status": "ok", "voice": "ru_RU-ruslan-medium"}
```

Aufbau des Abbilds: `python:3.11-slim`, `pip install piper-tts`, dann **beim Bauen**
`python3 -m piper.download_voices $PIPER_VOICE`. Das Modell liegt damit im Abbild statt in einem
Volume: rund 60 MB mehr Abbildgröße, dafür kein Erstlauf-Download, sofortige Einsatzbereitschaft und
Betrieb ohne Internet. (Bei Ollama wäre das Modell dafür zu groß — hier nicht.)

Synthese über die Python-Schnittstelle:

```python
from piper import PiperVoice, SynthesisConfig

voice = PiperVoice.load(MODEL_PATH)
config = SynthesisConfig(volume=PIPER_VOLUME, length_scale=PIPER_LENGTH_SCALE)
with wave.open(buffer, "wb") as wav_file:
    voice.synthesize_wav(text, wav_file, syn_config=config)
```

Das Modell wird **einmal beim Start** geladen, nicht je Anfrage — `PiperVoice.load` liest eine
ONNX-Datei und ist zu teuer für jeden Aufruf.

Umgebungsvariablen:

| Variable | Vorgabe | Zweck |
|---|---|---|
| `PIPER_VOICE` | `ru_RU-ruslan-medium` | Stimme; Alternativen `denis`, `dmitri`, `irina` |
| `PIPER_LENGTH_SCALE` | `1.0` | Tempo, größer heißt langsamer |
| `PIPER_VOLUME` | `1.0` | Lautstärke |

Die Vorgabe ist eine Männerstimme, weil der Nutzer die weibliche als zu leise empfand. Welche der drei
am besten klingt, entscheidet er nach einem Hörvergleich (siehe Abschnitt 7).

### 3.2 Der Endpunkt im Backend

```
GET /api/audio?text=<urlkodiert>   →  audio/wav
GET /api/audio/health              →  {"available": true|false}
```

`/api/audio/health` meldet, ob der `tts`-Dienst antwortet. Das Frontend fragt es einmal beim Start, um
seine Rückfallstufe zu bestimmen (Abschnitt 4).

**Der Text steht in der URL, nicht eine Aufgaben-Kennung.** Das ist einfacher und verrät nichts Neues
— der zu sprechende Text liegt seit der vorigen Ausbaustufe ohnehin beim Client. Eine Begrenzung auf
**300 Zeichen** verhindert Missbrauch als allgemeiner Sprachdienst; längere Anfragen liefern `400`.

Ist der `tts`-Dienst nicht erreichbar, antwortet der Endpunkt mit `503` — nie mit einem Serverfehler.
Das Frontend wertet das als Signal, auf die Browserstimme zu wechseln.

Der Aufruf läuft über `httpx`, das im Backend bereits für Ollama benutzt wird — ein eigener Client
nach dem Muster von `ollama_client.py`, damit die Anbindung an einen fremden Dienst an einer Stelle
liegt und in Tests austauschbar ist. „Nicht erreichbar" heißt: Verbindungsfehler oder eine Antwort,
die länger als **10 Sekunden** braucht. Für `/api/audio/health` gilt eine kürzere Frist von
**2 Sekunden**, denn dort wartet das Frontend beim Start darauf.

Fragen zwei Abrufe gleichzeitig denselben, noch nicht erzeugten Satz an, rechnet Piper ihn zweimal.
Das wird hingenommen: die App hat einen Benutzer, und eine Sperre je Schlüssel wäre mehr Maschinerie
als Nutzen.

### 3.3 Zwischenspeicher mit Deckel

Verzeichnis `/data/audio/` im vorhandenen `backend_data`-Volume. Dateiname ist ein `sha256` über
`voice | length_scale | text`, sodass der Schlüssel den Inhalt vollständig bestimmt.

Weil der Schlüssel inhaltsbestimmt ist, trägt die Antwort `Cache-Control: public, max-age=31536000,
immutable`. Damit speichert schon der Browser die Datei und fragt kein zweites Mal nach — das ist der
eigentliche Beschleuniger.

**Der Deckel:** `AUDIO_CACHE_MAX_MB` (Vorgabe 50). Nach jedem Schreiben wird die Gesamtgröße geprüft;
liegt sie darüber, werden die am längsten nicht benutzten Dateien gelöscht, bis sie darunter liegt.

Entscheidend dabei: **bei jedem Treffer wird der Zeitstempel der Datei aufgefrischt.** Ohne das wäre
es „ältester zuerst" statt „am längsten nicht gebraucht", und ausgerechnet die Sätze aus Einheit 1,
die in der Wiederholung ständig vorkommen, würden zuerst verschwinden.

Zur Größenordnung: Piper liefert WAV mit 22 kHz, 16 Bit, Mono — rund 44 KB je Sekunde, ein
Drei-Sekunden-Satz also etwa 130 KB. Der gesamte Kurs käme ungedeckelt auf 60 bis 100 MB. Der Deckel
ist deshalb kein Schmuck, sondern der Grund, warum die App klein bleibt.

## 4. Frontend: drei Stufen

| Stufe | Bedingung | Verhalten |
|---|---|---|
| 1 | `/api/audio/health` meldet `available` | Ton vom Server |
| 2 | Server stumm, Browserstimme vorhanden | `SpeechSynthesis` wie bisher |
| 3 | beides nicht | Textfassung der Aufgabe (unverändert aus der vorigen Stufe) |

Neu ist `audio/serverSpeech.ts` mit dem Bauen der URL, dem Vorladen und dem Abspielen. Der
`SpeechContext` wird zum Vermittler: er kennt beide Quellen und entscheidet je Aufruf.

Scheitert das Abspielen einer einzelnen Datei trotz `available`, fällt **dieser** Aufruf auf die
Browserstimme zurück und die Stufe wird dauerhaft heruntergesetzt — ein einmal als tot erkannter
Dienst wird nicht bei jedem Klick erneut probiert.

**Vorladen:** Beim Betreten einer Aufgabe holt das Frontend die Tondatei per `fetch` vor. Der Browser
legt sie wegen `immutable` in seinen HTTP-Zwischenspeicher; der spätere Klick auf den Lautsprecher
spielt ohne Wartezeit ab. Aktives Verwerfen beim Aufgabenwechsel findet **nicht** statt — der
HTTP-Zwischenspeicher räumt selbst auf, und in der Wiederholungsrunde werden dieselben Sätze wieder
gebraucht.

**„Langsam" erzeugt keine zweite Datei.** Das `<audio>`-Element spielt mit `playbackRate = 0.6` und
`preservesPitch = true` langsamer, ohne die Stimme zu vertiefen. Das spart je Satz einen zweiten
Eintrag — bei einem gedeckelten Speicher zählt das doppelt. Für die Browserstimme (Stufe 2) bleibt es
beim bisherigen `SLOW_RATE`.

## 5. Was aus der bisherigen Tonschicht wird

Sie bleibt vollständig erhalten und rutscht auf Stufe 2. Unverändert weiter gelten `speech.ts`
(`stripStress`, `pickRussianVoice`, `speak`), die Behandlung abgebrochener Ausgaben als Nicht-Fehler
und der Kopfzeilen-Schalter.

Zwei Anpassungen:

- Die Profilanzeige „Aktive Stimme" nennt künftig auch die Serverstimme, nicht nur die des Browsers.
- `available` im `SpeechContext` heißt ab jetzt „es gibt überhaupt Ton", also Stufe 1 **oder** 2. Nur
  wenn beides fehlt, greift der Textrückfall.

## 6. Tests

**`tts`-Dienst** (`tts/tests/`, pytest): Der Endpunkt liefert WAV-Bytes, leerer Text ergibt `400`,
`/health` nennt die konfigurierte Stimme. `PiperVoice` wird durch eine Attrappe ersetzt — ein 60-MB-
Modell in der Testsuite zu laden wäre absurd und würde die Läufe an einen Download binden.

**Backend:** gleicher Text ergibt denselben Schlüssel; ein Treffer fragt den `tts`-Dienst nicht; der
Deckel löscht die am längsten ungenutzte Datei und nicht die älteste; ein Treffer frischt den
Zeitstempel auf; Text über 300 Zeichen ergibt `400`; ein nicht erreichbarer `tts`-Dienst ergibt `503`;
`/api/audio/health` meldet beide Fälle korrekt.

**Frontend (Vitest):** URL-Bau, Vorladen, und alle drei Stufen — insbesondere der Wechsel von Stufe 1
auf 2 mitten im Betrieb, wenn das Abspielen scheitert.

**Playwright:** Der `tts`-Container läuft in den e2e-Läufen nicht. Der Audio-Endpunkt wird über
`page.route` abgefangen und liefert eine winzige WAV-Datei. Ein Fall prüft, dass ein `503` sauber auf
die Browserstimme zurückfällt. Die bestehende `speechSynthesis`-Attrappe aus `e2e/fixtures.ts` bleibt.

**`make smoke`:** eine Prüfung, dass `/api/audio` am laufenden Stack echten Ton liefert. Das ist die
einzige Stelle, an der echtes Piper mitspielt.

## 7. Stimmenvergleich

Im Implementierungsplan steht ein eigener Schritt: denselben Kurssatz mit `ruslan`, `denis` und
`dmitri` rendern und die drei Dateien dem Nutzer zum Hören geben. Erst danach wird die Vorgabe für
`PIPER_VOICE` endgültig festgelegt. Eine Stimme nach Aktenlage zu wählen wäre bei einem
Sprachlernprogramm die falsche Reihenfolge.

## 8. Bewusst nicht enthalten

- **Betonung aus dem Content.** Bräuchte die espeak-Abspaltung, siehe Abschnitt 2.
- **Komprimierte Formate** (Opus, MP3). Bräuchte ffmpeg im Abbild; im lokalen Netz ist WAV schnell
  genug, und der Deckel begrenzt den Platzbedarf ohnehin.
- **Stimmenwahl zur Laufzeit.** `PIPER_VOICE` ist eine Umgebungsvariable, kein Bedienelement. Ein
  Wechsel verlangt einen Neustart des Containers und entwertet den Zwischenspeicher (die Stimme geht
  in den Schlüssel ein).
- **Aussprachebewertung per Mikrofon.** Weiterhin ein eigenes Projekt.
