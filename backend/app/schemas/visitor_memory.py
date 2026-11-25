"""Schémas Pydantic de la mémoire temporaire des conversations visiteurs (SA-26)."""

from datetime import datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.config import settings
from app.models.enums import LanguageCode, MessageRole

ShortText = Annotated[str, Field(min_length=1, max_length=300)]


class MemoryMessageIn(BaseModel):
    """Message à enregistrer dans la mémoire de la session."""

    role: MessageRole = MessageRole.user
    content: str = Field(min_length=1)

    @field_validator("content")
    @classmethod
    def _check_length(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("le message ne peut pas être vide")
        if len(value) > settings.VISITOR_MESSAGE_MAX_LENGTH:
            raise ValueError(
                f"message trop long (maximum {settings.VISITOR_MESSAGE_MAX_LENGTH} caractères)"
            )
        return value


class MemoryMessageOut(BaseModel):
    """Message tel qu'il est conservé dans la mémoire."""

    role: MessageRole
    content: str
    created_at: datetime


class VisitorFacts(BaseModel):
    """Informations utiles déjà obtenues sur le visiteur (liste fermée de champs).

    Les champs reprennent ceux de la table `candidates` (bac_section, average_grade,
    preferred_language) et de son profil JSON (intérêts, objectifs, contraintes).
    """

    model_config = ConfigDict(extra="forbid")  # refuse tout champ non prévu (422)

    bac_section: Annotated[str, Field(max_length=60)] | None = None
    average_grade: Annotated[Decimal, Field(ge=0, le=20, decimal_places=2)] | None = None
    preferred_language: LanguageCode | None = None
    preferred_institution: Annotated[str, Field(max_length=10)] | None = None
    interests: Annotated[list[ShortText], Field(max_length=10)] | None = None
    goals: ShortText | None = None
    constraints: ShortText | None = None


class VisitorMemoryOut(BaseModel):
    """Mémoire complète de la session : ce que l'agent IA lira avant de répondre."""

    messages: list[MemoryMessageOut]
    facts: VisitorFacts
    max_messages: int = Field(description="Nombre maximal de messages conservés")
    expires_in_seconds: int = Field(description="Temps restant avant effacement de la mémoire")