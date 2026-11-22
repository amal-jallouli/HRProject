"""Classe de base déclarative pour tous les modèles SQLAlchemy."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base commune des modèles ORM (métadonnées, conventions)."""
