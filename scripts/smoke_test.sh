#!/usr/bin/env bash
# scripts/smoke_test.sh — prüft einen laufenden Speaker-Backend-Stack.
set -euo pipefail

BASE="${BASE:-http://localhost:8000}"

echo "1/5 Health"
curl -sf "$BASE/api/health" | grep -q '"status":"ok"'

echo "2/5 Kursübersicht"
curl -sf "$BASE/api/course" | grep -q '"stages"'

echo "3/5 Einheit 6 mit Regel und Aufgaben"
curl -sf "$BASE/api/units/6" | grep -q '"grammar_focus"'

echo "4/5 Einstufung startet"
curl -sf -X POST "$BASE/api/screening/start" | grep -q '"probe"'

echo "5/5 Wiederholung antwortet"
curl -sf "$BASE/api/review/due" | grep -q '"left"'

echo "OK — Backend antwortet auf allen Kurs-Endpunkten."
