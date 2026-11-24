"""Paramètres de l'application, chargés depuis les variables d'environnement."""

import json
from functools import lru_cache
from pathlib import Path
from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

# backend/app/core/config.py -> backend/ -> racine du dépôt
BACKEND_DIR = Path(__file__).resolve().parents[2]
ROOT_DIR = BACKEND_DIR.parent


class Settings(BaseSettings):
    """Configuration typée de l'API, alimentée par le fichier `.env`."""

    model_config = SettingsConfigDict(
        env_file=(ROOT_DIR / ".env", BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Application ---
    PROJECT_NAME: str = "SmartCampus AI"
    VERSION: str = "0.1.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # --- API ---
    API_V1_PREFIX: str = "/api/v1"
    BACKEND_CORS_ORIGINS: Annotated[list[str], NoDecode] = ["http://localhost:3000"]

    # --- Base de données ---
    DATABASE_URL: str = (
        "postgresql+psycopg://smartcampus_app:smartcampus_app@localhost:5432/smartcampus"
    )

    # --- Redis ---
    REDIS_URL: str = "redis://localhost:6379/0"
    

    # --- Sessions visiteurs (SA-25) ---
    # Durée de vie d'une session visiteur, en minutes (expiration automatique par Redis)
    VISITOR_SESSION_TTL_MINUTES: int = 60
    # Nombre maximal de requêtes par minute pour une même session
    VISITOR_RATE_LIMIT_PER_MINUTE: int = 30
    # Nombre maximal de messages qu'un visiteur peut envoyer dans une session
    VISITOR_MAX_MESSAGES_PER_SESSION: int = 50
    # Nombre maximal de sessions créées par adresse IP et par heure
    VISITOR_MAX_SESSIONS_PER_IP_PER_HOUR: int = 10 
    
    # --- Mémoire temporaire des conversations (SA-26) ---
    # Nombre de derniers messages conservés par session (les plus anciens sont supprimés)
    VISITOR_MEMORY_MAX_MESSAGES: int = 20
    # Longueur maximale d'un message enregistré, en caractères
    VISITOR_MESSAGE_MAX_LENGTH: int = 2000
    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        """Accepte une liste JSON ou une chaîne d'origines séparées par des virgules."""
        if isinstance(value, str):
            value = value.strip()
            if value.startswith("["):
                return json.loads(value)
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    """Retourne une instance unique (mise en cache) des settings."""
    return Settings()


settings = get_settings()
