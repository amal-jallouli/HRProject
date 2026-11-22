-- ============================================================
-- SmartCampus AI - Initialisation PostgreSQL
-- Exécuté automatiquement au premier démarrage du conteneur `db`.
-- ============================================================

-- pgvector : recherche de similarité vectorielle (RAG IIT/ISB)
CREATE EXTENSION IF NOT EXISTS vector;

-- pgcrypto : fonctions cryptographiques (gen_random_uuid, digest...)
CREATE EXTENSION IF NOT EXISTS pgcrypto;
