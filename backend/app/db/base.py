"""Classe de base déclarative pour tous les modèles SQLAlchemy."""

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

# Convention de nommage : des noms de contraintes prévisibles et stables,
# indispensables pour que les migrations Alembic restent reproductibles.
NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Base commune des modèles ORM (métadonnées, conventions)."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)
