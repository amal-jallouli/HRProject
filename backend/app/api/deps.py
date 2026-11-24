"""Dépendances FastAPI partagées : session DB, pagination, utilisateur courant et rôles.

⚠️ TEMPORAIRE (SA-19) : l'authentification réelle (JWT, mots de passe) arrive avec SA-28.
En attendant, l'utilisateur est identifié par l'en-tête `X-User-Email`, et seulement en
environnement `development` / `test`. Hors de ces environnements, personne n'est
authentifié (401), donc rien n'est exposé par erreur. SA-28 remplacera uniquement
`get_current_user_optional` ; `get_current_user` et `require_roles` resteront identiques.
"""

from collections.abc import Callable
from datetime import date
from typing import Annotated

from fastapi import Depends, HTTPException, Query, status
from fastapi.security import APIKeyHeader
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models import User
from app.models.enums import UserRole

_email_header = APIKeyHeader(name="X-User-Email", auto_error=False)
_STAND_IN_ENVIRONMENTS = {"development", "test"}


DbSession = Annotated[Session, Depends(get_db)]


def get_today() -> date:
    """Date du jour (dépendance séparée pour pouvoir la fixer dans les tests)."""
    return date.today()


Today = Annotated[date, Depends(get_today)]


def get_current_user_optional(
    db: DbSession, email: Annotated[str | None, Depends(_email_header)]
) -> User | None:
    if not email or settings.ENVIRONMENT not in _STAND_IN_ENVIRONMENTS:
        return None
    return db.scalar(select(User).where(User.email == email))


def get_current_user(
    user: Annotated[User | None, Depends(get_current_user_optional)],
) -> User:
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Authentification requise")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_roles(*roles: UserRole) -> Callable[[User], User]:
    """Autorise uniquement les rôles donnés (sinon 403)."""

    def checker(user: CurrentUser) -> User:
        if user.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Accès refusé pour ce rôle")
        return user

    return checker


# Gestion du catalogue : responsable académique (de son institution) et admin
CatalogueManager = Annotated[User, Depends(require_roles(UserRole.academic, UserRole.admin))]


class PageParams:
    def __init__(
        self,
        page: Annotated[int, Query(ge=1)] = 1,
        size: Annotated[int, Query(ge=1, le=100)] = 20,
    ) -> None:
        self.page = page
        self.size = size

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.size


Pagination = Annotated[PageParams, Depends()]
