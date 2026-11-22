# SmartCampus AI

Plateforme agentique d'orientation universitaire (IIT / ISB) — Projet n°3, IA générative, 2026-2027.

Le système engage une conversation naturelle (français, dialecte tunisien, Arabizi ; texte ou audio)
pour comprendre le candidat, construire progressivement son profil, recommander des parcours justifiés
via un RAG sur le corpus officiel IIT/ISB, puis orchestrer la préinscription, le QCM, le rendez-vous
et le suivi jusqu'à l'inscription.

> État actuel : **socle technique initialisé** (backlog SA-6 → SA-9).
> Aucune logique métier, aucun modèle de données ni agent ne sont encore implémentés.

## Stack technique

| Couche | Technologie |
| --- | --- |
| Frontend | Next.js (App Router) · React · TypeScript · Tailwind CSS · shadcn/ui |
| Backend | FastAPI · Python 3.12 · SQLAlchemy 2.0 · Alembic |
| Base de données | PostgreSQL 16 + pgvector |
| Cache / files d'attente | Redis 7 |
| Agents & RAG | LangGraph, Whisper, pgvector *(épics suivants)* |
| Infrastructure locale | Docker Compose (db, redis, pgadmin) |

## Prérequis

- Python ≥ 3.11
- Node.js ≥ 20 et npm
- Docker Desktop (ou Docker Engine + Compose v2)
- `make` (optionnel, mais recommandé)

## Démarrage rapide

```bash
# 1. Variables d'environnement
cp .env.example .env
cp .env.example frontend/.env.local   # ou ajustez NEXT_PUBLIC_API_URL

# 2. Infrastructure : PostgreSQL (+pgvector), Redis, pgAdmin
make up            # équivaut à : docker compose up -d

# 3. Backend
make backend-install
make backend-run    # -> http://localhost:8000/docs

# 4. Frontend
make frontend-install
make frontend-dev    # -> http://localhost:3000
```

### URLs utiles

| Service | URL |
| --- | --- |
| API (racine) | http://localhost:8000 |
| Documentation Swagger | http://localhost:8000/docs |
| Health check | http://localhost:8000/api/v1/health |
| Frontend | http://localhost:3000 |
| Test de liaison API | http://localhost:3000/chat |
| pgAdmin | http://localhost:5050 |

## Structure du projet

```
smartcampus-ai/
├── backend/          # API FastAPI (SA-7)
├── frontend/         # Application Next.js (SA-8)
├── docker/           # Configuration d'infrastructure (postgres/init.sql)
├── docs/diagrams/    # Schémas d'architecture (SA-3 / SA-4)
├── data/             # Jeux de données / corpus RAG (épics suivants)
├── scripts/          # Scripts utilitaires
├── docker-compose.yml
├── Makefile
└── .env.example
```

## Commandes `make`

| Commande | Description |
| --- | --- |
| `make help` | Affiche toutes les commandes disponibles |
| `make env` | Crée `.env` à partir de `.env.example` |
| `make up` / `make down` | Démarre / arrête l'infrastructure Docker |
| `make logs` | Suit les logs des conteneurs |
| `make backend-install` | Crée le venv et installe les dépendances backend |
| `make backend-run` | Lance l'API en mode rechargement |
| `make backend-test` | Exécute les tests pytest |
| `make frontend-install` | Installe les dépendances npm du frontend |
| `make frontend-dev` | Lance le serveur de développement Next.js |
| `make frontend-build` | Build de production du frontend |
| `make lint` | Lint backend (ruff) + frontend (eslint) |
| `make clean` | Supprime les artefacts de build et volumes Docker |

## Backlog

| ID | Titre | Statut |
| --- | --- | --- |
| SA-6 | Initialisation Backend et Frontend | ✅ |
| SA-7 | Initialiser le backend | ✅ |
| SA-8 | Initialiser le Frontend | ✅ |
| SA-9 | Préparer l'environnement de développement local | ✅ |

## Licence

Projet académique — Institut International de Technologie (IIT), Université Nord-Américaine Privée.
