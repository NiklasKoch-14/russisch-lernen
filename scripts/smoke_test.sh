#!/usr/bin/env bash
# scripts/smoke_test.sh — prüft einen laufenden Speaker-Backend-Stack.
set -euo pipefail

BASE="${BASE:-http://localhost:8000}"

echo "1/7 Health"
curl -sf "$BASE/api/health" | grep -q '"status":"ok"'

echo "2/7 Kursübersicht"
curl -sf "$BASE/api/course" | grep -q '"stages"'

echo "3/7 Einheit 6 mit Regel und Aufgaben"
curl -sf "$BASE/api/units/6" | grep -q '"grammar_focus"'

echo "4/7 Einstufung startet"
curl -sf -X POST "$BASE/api/screening/start" | grep -q '"probe"'

echo "5/7 Wiederholung antwortet"
curl -sf "$BASE/api/review/due" | grep -q '"left"'

echo "6/7 Sprachdienst erreichbar"
curl -sf "$BASE/api/audio/health" | grep -q '"available":true'

echo "7/7 Ton wird erzeugt"
curl -sf "$BASE/api/audio?text=%D0%B4%D0%BE%D0%BC" -o /tmp/speaker-smoke.wav
test "$(stat -c%s /tmp/speaker-smoke.wav)" -gt 1000
rm -f /tmp/speaker-smoke.wav

echo "OK — Backend antwortet auf allen Kurs-Endpunkten und liefert Ton."
