# Speaker — KI-Sprachlern-App: Design

Datum: 2026-07-21
Status: Genehmigt

## 1. Ziel

Eine selbst-gehostete Sprachlern-App (angelehnt an Duolingo/Babbel-Prinzipien), bei der der Hauptfokus auf
gesprochenen Dialogen mit einem KI-Tutor liegt. Der Tutor merkt sich den aktuellen Sprachstand des Nutzers,
erstellt darauf zugeschnittene Lernpläne und erzeugt regelmäßig Vokabel-Karteikarten mit Tests. Start-Sprache:
Englisch (Nutzer ist deutschsprachig), Architektur aber von Anfang an sprachagnostisch.

**Harte Randbedingung:** keine eigenen API-Kosten — kein API-Key wird konfiguriert. Alle KI-Fähigkeiten
(Textgenerierung, Spracherkennung, Sprachsynthese) laufen lokal via Ollama/Open-Source-Modelle. Deployment
komplett über Docker. Zielumgebung ist CPU-only (kein GPU im Zielsystem erkannt).

Nutzerkreis: Single-User (nur der Betreiber selbst), kein Auth/Login nötig.

## 2. Phasierung

- **Phase 1** (dieser Plan): Text-basierter Dialog mit KI-Tutor, Proficiency-Tracking, Lernplan-Generierung,
  Vokabel-Karteikarten mit Spaced-Repetition-Tests. Komplett in Docker, noch ohne Mikrofon/Voice.
- **Phase 2** (später, eigener Spec/Plan): Voice-Layer — Speech-to-Text (Aufnahme via Mikrofon) und
  Text-to-Speech werden in den bestehenden Dialog-Flow aus Phase 1 integriert, sodass derselbe Dialog auch
  gesprochen geführt werden kann.

Diese Aufteilung reduziert Risiko: Die Kernlogik (Tutor-Persona, Lernplan, SRS) wird zuerst mit Text
verifiziert, bevor die aufwändigere Audio-Pipeline (STT/TTS auf CPU) dazukommt.

## 3. Architektur

Drei Docker-Container via `docker-compose.yml`:

- **frontend** — React-SPA (Vite), Auslieferung via nginx, Port 3000. UI-Sprache Deutsch; Lerninhalte in der
  gewählten Zielsprache. In Phase 1 ein Text-Chat-Interface; Phase 2 ergänzt Mikrofon-Aufnahme/Audio-Playback.
- **backend** — Python/FastAPI, ein Prozess mit klar getrennten Modulen:
  - Dialog-Orchestrierung (Prompt-Bau, Ollama-Chat-Aufrufe, Konversationsverlauf)
  - Proficiency-/Lernplan-Logik (Einstufung, laufende Anpassung, Plan-Generierung)
  - Karteikarten-/SRS-Logik (SM-2-Algorithmus)
  - Persistenz (SQLite)
  - (Phase 2) STT (faster-whisper) und TTS (Piper) als zusätzliche Module
- **ollama** — offizielles `ollama/ollama`-Image. Lädt beim ersten Start automatisch ein konfigurierbares
  Modell (Default `llama3.2:3b`, per Env-Var austauschbar). Kein API-Key, rein lokal.

Alle drei Services kommunizieren über ein internes Docker-Netzwerk. Volumes sichern SQLite-DB und
Ollama-Modell-Cache über Neustarts hinweg. Ein einzelner `docker compose up` startet die gesamte App;
der erste Start dauert länger wegen des Modell-Downloads.

## 4. Datenmodell (SQLite)

- **Profile** (genau eine Zeile, Single-User): aktive Sprache, CEFR-Level pro Sprache, erstellt_am
- **LearningPlan**: aktuelle Fokus-Themen/Szenarien (z.B. "Restaurant-Smalltalk", "Über das Wochenende
  erzählen"), von der KI generiert, als strukturiertes JSON, mit Gültigkeits-/Erstellungszeitpunkt
- **ConversationSession**: Liste von Turns (Rolle: user/assistant, Text, Zeitstempel), zugehörige
  Analyse-Notizen (erkannte Fehler, Level-Einschätzung nach dieser Session)
- **VocabCard**: Begriff, Übersetzung, Beispielsatz, Sprache, SM-2-Felder (Intervall, Ease-Factor,
  Wiederholungszähler, Fälligkeitsdatum), erstellt_am, Quelle (aus welcher Session generiert)
- **QuizAttempt**: card_id, Zeitstempel, Nutzer-Antwort, korrekt (bool)

## 5. Dialog-Flow (Phase 1: text-basiert)

1. Nutzer tippt eine Nachricht im Chat-Interface
2. Backend baut den Prompt: System-Prompt (Tutor-Persona, Zielsprache, aktuelles CEFR-Level, aktueller
   Lernplan-Fokus, relevanter Konversationsverlauf) + Nutzer-Eingabe
3. Ollama-Chat-Call liefert die Tutor-Antwort (in der Zielsprache, korrigiert Fehler behutsam, bleibt beim
   aktuellen Lernplan-Thema, ermutigender Ton)
4. Antwort wird als Chat-Bubble angezeigt und in der Session persistiert

Der Prompt-Bau-Mechanismus wird so gestaltet, dass er in Phase 2 unverändert wiederverwendet werden kann —
nur die Ein-/Ausgabe-Modalität (Audio statt Text) kommt hinzu, ohne die Orchestrierungslogik zu ändern.

## 6. Proficiency & Lernplan

- **Erster Start:** kurzer Einstufungsdialog — der Tutor stellt einige Fragen steigender Schwierigkeit;
  basierend auf den Antworten schätzt die KI ein initiales CEFR-Level (A1–C2), das im Profile gespeichert wird
- **Nach jeder Session:** Hintergrund-Analyse-Schritt — die KI bewertet das Transkript und liefert strukturiert
  zurück: ggf. aktualisiertes Level, auffällige Fehler, Vokabel-Vorschläge, nächste sinnvolle Themen
- **Lernplan-Regenerierung:** periodisch (z.B. alle N Sessions oder bei Level-Wechsel) erzeugt die KI einen
  neuen kurzen strukturierten Plan mit anstehenden Dialog-Themen/Szenarien passend zum aktuellen Level; der
  jeweils aktuelle Fokus fließt in den System-Prompt der nächsten Session ein

## 7. Karteikarten & Vokabeltest

- Nach einer Konversationssession extrahiert die KI eine kleine Menge neuer/relevanter Vokabeln (neue Wörter
  für das aktuelle Level, oder Wörter, bei denen der Nutzer sichtlich Schwierigkeiten hatte) und legt daraus
  neue `VocabCard`-Einträge an
- Eigene "Vokabeltraining"-Ansicht zeigt fällige Karten nach SM-2-Scheduling
- Test-Format: getippte Antwort (Übersetzung), Bewertung per normalisiertem String-Vergleich mit
  Toleranz (z.B. Levenshtein-Schwellenwert) für Tippfehler/Groß-Kleinschreibung
- Die App schlägt eine Quiz-Runde vor, sobald genügend Karten fällig sind (z.B. Schwellenwert konfigurierbar)

## 8. Deployment

`docker compose up` startet Frontend, Backend und Ollama. Kein API-Key wird je abgefragt oder benötigt.
Modellwahl (Ollama-Modell, Whisper-/Piper-Modellgröße für Phase 2) ist über Environment-Variablen in der
`docker-compose.yml` konfigurierbar, mit sinnvollen CPU-tauglichen Defaults.

## 9. Testing

- **Backend:** pytest für SM-2-Algorithmus-Korrektheit, Prompt-Bau-Funktionen, DB-Layer (temporäre SQLite),
  API-Endpunkte (Ollama-Aufrufe gemockt)
- **Frontend:** Vitest/Testing-Library für Chat- und Karteikarten-Komponenten
- **Integration:** Smoke-Test-Skript gegen den echten docker-compose-Stack (ein Text-Dialog-Turn end-to-end),
  um die Ollama-Anbindung zu verifizieren

## 10. Out of Scope (Phase 1)

- Mikrofon-Aufnahme, Speech-to-Text, Text-to-Speech (→ Phase 2)
- Mehrere Nutzer/Accounts/Login
- Unterstützung weiterer Sprachen mit tatsächlichen Inhalten (Architektur ist vorbereitet, aber nur Englisch
  wird initial befüllt)
- Grammatik-Drills/Übungen abseits von Dialog und Vokabel-Karteikarten
