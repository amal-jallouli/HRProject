"""Schémas Pydantic des sessions visiteurs (SA-25)."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class VisitorSessionLimits(BaseModel):
    """Limites d'utilisation appliquées à une session visiteur."""

    requests_per_minute: int
    max_messages: int


class VisitorSessionOut(BaseModel):
    """État d'une session visiteur (sans le jeton secret)."""

    session_id: uuid.UUID
    created_at: datetime
    expires_at: datetime
    expires_in_seconds: int = Field(description="Temps restant avant expiration")
    is_valid: bool
    messages_used: int
    messages_remaining: int
    limits: VisitorSessionLimits


class VisitorSessionCreated(VisitorSessionOut):
    """Réponse à la création : contient le jeton, renvoyé UNE SEULE FOIS."""

    token: str = Field(
        description="Jeton à conserver côté client et à envoyer dans l'en-tête X-Visitor-Token"
    )