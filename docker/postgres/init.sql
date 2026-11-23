-- ============================================================
-- SmartCampus AI - Initialisation PostgreSQL
-- Exécuté automatiquement au premier démarrage du conteneur `db`
-- (volume vide uniquement), en tant que superutilisateur.
-- ============================================================

-- 1. Extensions (nécessitent les droits superutilisateur)
-- pgvector : recherche de similarité vectorielle (RAG IIT/ISB)
CREATE EXTENSION IF NOT EXISTS vector;
-- pgcrypto : fonctions cryptographiques
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- 2. Utilisateur applicatif à droits limités
--    Le nom et le mot de passe viennent des variables d'environnement
--    APP_DB_USER / APP_DB_PASSWORD (\getenv, psql 15+).
\getenv app_user APP_DB_USER
\getenv app_password APP_DB_PASSWORD
SELECT current_database() AS dbname \gset

CREATE ROLE :"app_user" WITH LOGIN PASSWORD :'app_password'
  NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION;

-- Il ne peut se connecter qu'à la base SmartCampus (pas aux autres bases)
REVOKE ALL ON DATABASE :"dbname" FROM PUBLIC;
REVOKE CONNECT ON DATABASE postgres FROM PUBLIC;
GRANT CONNECT, TEMPORARY ON DATABASE :"dbname" TO :"app_user";

-- Il possède le schéma public : Alembic peut y créer les tables (SA-17)
ALTER SCHEMA public OWNER TO :"app_user";