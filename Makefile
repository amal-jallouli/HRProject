# ============================================================
# SmartCampus AI - Commandes de développement local
# Aide : make help
# Compatible Linux/macOS et Windows (Git Bash / WSL / msys).
# ============================================================

.DEFAULT_GOAL := help

BACKEND_DIR  := backend
FRONTEND_DIR := frontend
VENV         := $(BACKEND_DIR)/.venv

# Chemins du venv selon l'OS (Windows: Scripts/, Unix: bin/)
ifeq ($(OS),Windows_NT)
  PY  := $(VENV)/Scripts/python.exe
  PIP := $(VENV)/Scripts/pip.exe
else
  PY  := $(VENV)/bin/python
  PIP := $(VENV)/bin/pip
endif

.PHONY: help env up down restart logs ps clean-volumes clean \
        backend-install backend-run backend-test backend-lint backend-format \
        frontend-install frontend-dev frontend-build frontend-lint \
        db-shell redis-cli lint \
				db-upgrade db-downgrade db-revision db-seed

help: ## Affiche cette aide
	@grep -hE '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

## --- Environnement -------------------------------------------------

.env: ## Crée .env à partir de .env.example
	@cp -n .env.example .env || true
	@echo ".env prêt."

env: .env ## Prépare le fichier .env

## --- Infrastructure Docker -----------------------------------------

up: .env ## Démarre PostgreSQL, Redis et pgAdmin
	docker compose up -d
	@echo "Services démarrés. pgAdmin : http://localhost:5050"

down: ## Arrête les conteneurs
	docker compose down

restart: down up ## Redémarre les conteneurs

logs: ## Suit les logs des conteneurs
	docker compose logs -f

ps: ## Liste l'état des conteneurs
	docker compose ps

clean-volumes: ## Supprime les conteneurs ET les volumes (données effacées)
	docker compose down -v

## --- Backend -------------------------------------------------------

backend-install: ## Crée le venv et installe les dépendances backend
	python -m venv $(VENV)
	$(PY) -m pip install --upgrade pip
	$(PY) -m pip install -e "$(BACKEND_DIR)[dev]"

backend-run: ## Lance l'API FastAPI (rechargement à chaud)
	$(PY) -m uvicorn app.main:app --reload --app-dir $(BACKEND_DIR) --host 0.0.0.0 --port 8000

backend-test: ## Exécute les tests backend (pytest)
	$(PY) -m pytest $(BACKEND_DIR) -q

backend-lint: ## Lint backend (ruff)
	$(PY) -m ruff check $(BACKEND_DIR)

backend-format: ## Formatage backend (ruff format)
	$(PY) -m ruff format $(BACKEND_DIR)

## --- Frontend ------------------------------------------------------

frontend-install: ## Installe les dépendances npm du frontend
	cd $(FRONTEND_DIR) && npm install

frontend-dev: ## Lance le serveur de développement Next.js
	cd $(FRONTEND_DIR) && npm run dev

frontend-build: ## Build de production du frontend
	cd $(FRONTEND_DIR) && npm run build

frontend-lint: ## Lint frontend (eslint)
	cd $(FRONTEND_DIR) && npm run lint

## --- Base de données (Alembic) -------------------------------------

db-upgrade: ## Applique les migrations (crée/met à jour les tables)
	$(PY) -m alembic -c $(BACKEND_DIR)/alembic.ini upgrade head

db-downgrade: ## Annule la dernière migration
	$(PY) -m alembic -c $(BACKEND_DIR)/alembic.ini downgrade -1

db-revision: ## Génère une migration : make db-revision m="message"
	$(PY) -m alembic -c $(BACKEND_DIR)/alembic.ini revision --autogenerate -m "$(m)"

db-seed: ## Insère les données de démonstration (idempotent)
	$(PY) -m app.db.seed

## --- Utilitaires ---------------------------------------------------

lint: backend-lint frontend-lint ## Lint backend + frontend

db-shell: ## Ouvre un shell psql dans le conteneur db
	docker compose exec db psql -U $${POSTGRES_USER:-smartcampus} -d $${POSTGRES_DB:-smartcampus}

redis-cli: ## Ouvre redis-cli dans le conteneur redis
	docker compose exec redis redis-cli

clean: ## Supprime les artefacts de build (venv, node_modules, caches)
	python -c "import pathlib, shutil; [shutil.rmtree(p, ignore_errors=True) for p in ['$(VENV)', '$(FRONTEND_DIR)/node_modules', '$(FRONTEND_DIR)/.next']]; [shutil.rmtree(p, ignore_errors=True) for p in pathlib.Path('.').rglob('__pycache__')]; [shutil.rmtree(p, ignore_errors=True) for p in pathlib.Path('.').rglob('.pytest_cache')]; [shutil.rmtree(p, ignore_errors=True) for p in pathlib.Path('.').rglob('.ruff_cache')]"
	@echo "Nettoyage terminé."
