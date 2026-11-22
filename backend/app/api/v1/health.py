"""Endpoint de santé : GET /api/v1/health."""

from fastapi import APIRouter
from sqlalchemy import text

from app.core.config import settings
from app.db.session import engine

router = APIRouter(tags=["health"])


def _database_status() -> str:
    """Teste rapidement la connexion à PostgreSQL sans faire échouer l'endpoint."""
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception:  # noqa: BLE001 - le health check ne doit jamais lever d'erreur
        return "down"
    return "up"


@router.get("/health", summary="État de santé de l'API")
def health() -> dict[str, object]:
    """Retourne l'état du service et de ses dépendances (base de données)."""
    return {
        "status": "ok",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "dependencies": {"database": _database_status()},
    }
