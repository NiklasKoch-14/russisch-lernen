# Speaker — lokaler Betrieb über Docker.
# `make help` listet alle Ziele.

COMPOSE ?= docker compose
SLOW_MO ?= 400
BACKEND_URL ?= http://localhost:8000
FRONTEND_URL ?= http://localhost:3000

.DEFAULT_GOAL := help
.PHONY: help deploy remove restart purge logs ps smoke validate test test-e2e test-e2e-show test-e2e-ui dev

help: ## Diese Übersicht anzeigen
	@grep -hE '^[a-z0-9-]+:.*?## ' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

deploy: ## Alle Container bauen und im Hintergrund starten
	$(COMPOSE) up -d --build
	@echo ""
	@echo "  Frontend: $(FRONTEND_URL)"
	@echo "  Backend:  $(BACKEND_URL)/api/health"
	@echo ""
	@echo "  Beim ersten Start lädt Ollama sein Modell herunter — das dauert."
	@echo "  Der Kurs funktioniert schon vorher; Ollama braucht nur die Fehlererklärung."
	@echo "  Fortschritt sehen: make logs"

remove: ## Container und Netzwerk stoppen und entfernen (Lernfortschritt bleibt erhalten)
	$(COMPOSE) down
	@echo "Container entfernt. Datenbank und Ollama-Modell liegen weiter in den Volumes."
	@echo "Wirklich alles löschen inklusive Lernfortschritt: make purge"

restart: ## Neu bauen und neu starten
	$(COMPOSE) up -d --build --force-recreate

purge: ## ACHTUNG: entfernt auch die Volumes — Lernfortschritt und Modell sind dann weg
	@printf 'Das löscht deinen Lernfortschritt und das Ollama-Modell. Fortfahren? [j/N] ' \
		&& read answer && [ "$$answer" = "j" ] || (echo "Abgebrochen."; exit 1)
	$(COMPOSE) down -v

logs: ## Logs aller Container mitlesen
	$(COMPOSE) logs -f

ps: ## Status der Container
	$(COMPOSE) ps

smoke: ## Rauchtest gegen den laufenden Stack
	BASE=$(BACKEND_URL) ./scripts/smoke_test.sh

validate: ## Kursinhalte prüfen
	cd backend && .venv/bin/python -m scripts.validate_content

test: ## Unit-Tests von Backend und Frontend
	cd backend && .venv/bin/pytest -q
	cd frontend && npm test

test-e2e: ## Playwright-Tests headless — der schnelle Standardlauf
	cd frontend && npx playwright test

test-e2e-show: ## Playwright-Tests im sichtbaren Browserfenster, verlangsamt zum Zuschauen
	@echo "Ein Chromium-Fenster geht auf. SLOW_MO=$(SLOW_MO)ms pro Aktion."
	cd frontend && SLOW_MO=$(SLOW_MO) npx playwright test --headed

test-e2e-ui: ## Playwright-Oberfläche: Tests einzeln starten, Schritte zurückspulen
	cd frontend && npx playwright test --ui

dev: ## Backend und Frontend lokal ohne Docker starten (zwei Terminals nötig)
	@echo "Terminal 1:  cd backend  && .venv/bin/uvicorn app.main:app --reload --port 8000"
	@echo "Terminal 2:  cd frontend && npm run dev"
