"""SA-13 : utilisateurs, candidats, conversations, orientation, préinscription, QCM, entretien."""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.catalogue import ACADEMIC_YEAR_REGEX
from app.models.enums import (
    AppointmentStatus,
    CandidateStatus,
    LanguageCode,
    MessageRole,
    NotificationType,
    RecommendationStatus,
    UserRole,
    pg_enum,
)

_UUID_PK = {"primary_key": True, "server_default": text("gen_random_uuid()")}
_NOW = text("now()")


class User(Base):
    """Compte de connexion : candidat inscrit, responsable académique, entretien ou admin."""

    __tablename__ = "users"
    __table_args__ = (
        # Un responsable académique est rattaché à une institution, les autres rôles non.
        CheckConstraint(
            "(role = 'academic') = (institution_id IS NOT NULL)",
            name="academic_has_institution",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), **_UUID_PK)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str | None] = mapped_column(String(150))
    role: Mapped[UserRole] = mapped_column(pg_enum(UserRole, "user_role"))
    institution_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("institutions.id", ondelete="RESTRICT"), index=True
    )


class Candidate(Base):
    """Personne qui souhaite étudier ; peut exister sans compte (visiteur du chat)."""

    __tablename__ = "candidates"
    __table_args__ = (
        CheckConstraint("average_grade BETWEEN 0 AND 20", name="average_grade_range"),
        Index("ix_candidates_status", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), **_UUID_PK)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), unique=True
    )
    full_name: Mapped[str | None] = mapped_column(String(150))
    email: Mapped[str | None] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(30))
    bac_section: Mapped[str | None] = mapped_column(String(60))
    average_grade: Mapped[Decimal | None] = mapped_column(Numeric(4, 2))
    preferred_language: Mapped[LanguageCode | None] = mapped_column(
        pg_enum(LanguageCode, "language_code")
    )
    status: Mapped[CandidateStatus] = mapped_column(
        pg_enum(CandidateStatus, "candidate_status"),
        server_default=CandidateStatus.visitor.value,
    )
    # Profil construit par la conversation : intérêts, objectifs, contraintes
    profile: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=_NOW)


class Conversation(Base):
    __tablename__ = "conversations"
    __table_args__ = (
        # Une conversation appartient à un candidat ou à un visiteur anonyme (jeton invité).
        CheckConstraint(
            "candidate_id IS NOT NULL OR guest_token_hash IS NOT NULL",
            name="has_owner",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), **_UUID_PK)
    candidate_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("candidates.id", ondelete="CASCADE"), index=True
    )
    guest_token_hash: Mapped[str | None] = mapped_column(String(128), unique=True)
    summary: Mapped[str | None] = mapped_column(Text)  # mémoire de contexte
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=_NOW)


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (
        Index("ix_messages_conversation_id_created_at", "conversation_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), **_UUID_PK)
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE")
    )
    role: Mapped[MessageRole] = mapped_column(pg_enum(MessageRole, "message_role"))
    content: Mapped[str] = mapped_column(Text)  # texte ou transcription audio
    audio_path: Mapped[str | None] = mapped_column(String(255))
    language: Mapped[LanguageCode | None] = mapped_column(pg_enum(LanguageCode, "language_code"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=_NOW)


class Recommendation(Base):
    __tablename__ = "recommendations"
    __table_args__ = (CheckConstraint("compatibility_score BETWEEN 0 AND 100", name="score_range"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), **_UUID_PK)
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("candidates.id", ondelete="CASCADE"), index=True
    )
    program_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("programs.id", ondelete="RESTRICT"), index=True
    )
    compatibility_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    justification: Mapped[str | None] = mapped_column(Text)
    sources: Mapped[list[Any] | None] = mapped_column(JSONB)  # passages RAG cités
    status: Mapped[RecommendationStatus] = mapped_column(
        pg_enum(RecommendationStatus, "recommendation_status"),
        server_default=RecommendationStatus.proposed.value,
    )
    validated_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )


class Preregistration(Base):
    __tablename__ = "preregistrations"
    __table_args__ = (
        UniqueConstraint("candidate_id", "program_id", "academic_year"),
        CheckConstraint(f"academic_year ~ '{ACADEMIC_YEAR_REGEX}'", name="academic_year_format"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), **_UUID_PK)
    candidate_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("candidates.id", ondelete="CASCADE"))
    program_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("programs.id", ondelete="RESTRICT"), index=True
    )
    academic_year: Mapped[str] = mapped_column(String(9))  # ex. 2026-2027
    consent_given_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    consent_version: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=_NOW)


class Qcm(Base):
    __tablename__ = "qcms"
    __table_args__ = (CheckConstraint("score BETWEEN 0 AND 100", name="score_range"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), **_UUID_PK)
    preregistration_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("preregistrations.id", ondelete="CASCADE"), unique=True
    )
    # Liste : question, options, bonne réponse, réponse du candidat
    questions: Mapped[list[Any]] = mapped_column(JSONB)
    score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    interview_summary: Mapped[str | None] = mapped_column(Text)


class Appointment(Base):
    __tablename__ = "appointments"
    __table_args__ = (CheckConstraint("ends_at > starts_at", name="ends_after_starts"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), **_UUID_PK)
    preregistration_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("preregistrations.id", ondelete="CASCADE"), index=True
    )
    interviewer_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[AppointmentStatus] = mapped_column(
        pg_enum(AppointmentStatus, "appointment_status"),
        server_default=AppointmentStatus.proposed.value,
    )
    outcome: Mapped[str | None] = mapped_column(String(50))  # résultat de l'entretien
    observations: Mapped[str | None] = mapped_column(Text)


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (Index("ix_notifications_scheduled_at", "scheduled_at"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), **_UUID_PK)
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("candidates.id", ondelete="CASCADE"), index=True
    )
    type: Mapped[NotificationType] = mapped_column(pg_enum(NotificationType, "notification_type"))
    subject: Mapped[str | None] = mapped_column(String(255))
    body: Mapped[str | None] = mapped_column(Text)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))  # NULL = non envoyé
