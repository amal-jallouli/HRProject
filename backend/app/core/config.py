"""Paramètres de l'application, chargés depuis les variables d'environnement."""

from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

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
    BACKEND_CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    # --- Base de données ---
    DATABASE_URL: str = "postgresql+psycopg://smartcampus:smartcampus@localhost:5432/smartcampus"

    # --- Redis ---
    REDIS_URL: str = "redis://localhost:6379/0"

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        """Accepte une liste JSON ou une chaîne d'origines séparées par des virgules."""
        if isinstance(value, str) and not value.strip().startswith("["):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    """Retourne une instance unique (mise en cache) des settings."""
    return Settings()


settings = get_settings()
