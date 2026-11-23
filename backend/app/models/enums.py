"""Énumérations métier, stockées comme types ENUM natifs PostgreSQL."""

import enum

from sqlalchemy import Enum as SAEnum


class UserRole(enum.StrEnum):
    candidate = "candidate"
    academic = "academic"
    interviewer = "interviewer"
    admin = "admin"


class ProgramLevel(enum.StrEnum):
    licence = "licence"
    prepa = "prepa"
    ingenierie = "ingenierie"
    autre = "autre"


class LanguageCode(enum.StrEnum):
    fr = "fr"
    tn = "tn"  # dialecte tunisien
    arabizi = "arabizi"


class CandidateStatus(enum.StrEnum):
    visitor = "visitor"  # en conversation, profil encore insuffisant
    profiled = "profiled"  # l'agent a collecté assez d'infos pour orienter
    preregistered = "preregistered"  # préinscription créée
    interview_scheduled = "interview_scheduled"  # rendez-vous confirmé
    enrolled = "enrolled"  # inscription finale
    abandoned = "abandoned"  # candidat inactif ou retiré


class MessageRole(enum.StrEnum):
    user = "user"
    assistant = "assistant"
    system = "system"
    tool = "tool"


class RecommendationStatus(enum.StrEnum):
    proposed = "proposed"
    validated = "validated"
    adjusted = "adjusted"
    rejected = "rejected"


class AppointmentStatus(enum.StrEnum):
    proposed = "proposed"
    confirmed = "confirmed"
    done = "done"
    cancelled = "cancelled"


class NotificationType(enum.StrEnum):
    confirmation = "confirmation"
    reminder = "reminder"
    followup = "followup"


class DocumentType(enum.StrEnum):
    brochure = "brochure"
    faq = "faq"
    conditions = "conditions"
    procedure = "procedure"


class DocumentStatus(enum.StrEnum):
    draft = "draft"
    indexed = "indexed"
    outdated = "outdated"


class PublicationStatus(enum.StrEnum):
    draft = "draft"  # en préparation, invisible pour les candidats et l'agent IA
    published = "published"  # officiel : visible s'il est dans sa période de validité
    archived = "archived"  # retiré, conservé pour l'historique


class JobStatus(enum.StrEnum):
    pending = "pending"
    running = "running"
    success = "success"
    failed = "failed"


def pg_enum(enum_cls: type[enum.Enum], name: str) -> SAEnum:
    """Type ENUM PostgreSQL nommé, stocké avec les *valeurs* (pas les noms Python)."""
    return SAEnum(
        enum_cls,
        name=name,
        values_callable=lambda e: [member.value for member in e],
    )
