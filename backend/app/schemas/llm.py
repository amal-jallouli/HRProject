"""Schémas de l'API de dialogue avec le LLM (SA-36)."""

from typing import Any

from pydantic import BaseModel, Field


class QuestionIn(BaseModel):
    message: str = Field(min_length=1, max_length=2000, description="Question du candidat")


class ReponseOut(BaseModel):
    reponse: str = Field(description="Réponse générée pour le candidat")
    intention: str | None = Field(description="Intention détectée (None si non comprise)")
    langue: str | None = Field(description="fr, tn_ar, arabizi ou mixte")
    profil: dict[str, Any] = Field(description="Informations du candidat extraites du message")
    repli: bool = Field(description="True si la demande n'a pas été comprise (reformulation)")
    modele: str
    latence_s: float


class StatutLLMOut(BaseModel):
    serveur: str = Field(description="up ou down")
    modele: str
    modele_installe: bool
