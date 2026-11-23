"""Modèles ORM de SmartCampus AI.

Tous les modèles sont importés ici : Alembic doit les connaître pour générer les migrations.
"""

from app.models.candidatures import (
    Appointment,
    Candidate,
    Conversation,
    Message,
    Notification,
    Preregistration,
    Qcm,
    Recommendation,
    User,
)
from app.models.catalogue import Institution, Program, ProgramYear, Subject
from app.models.documents import AgentRun, Document, DocumentChunk, SyncJob

__all__ = [
    "AgentRun",
    "Appointment",
    "Candidate",
    "Conversation",
    "Document",
    "DocumentChunk",
    "Institution",
    "Message",
    "Notification",
    "Preregistration",
    "Program",
    "ProgramYear",
    "Subject",
    "Qcm",
    "Recommendation",
    "SyncJob",
    "User",
]
