"""SA-12 : catalogue académique (institutions, formations, conditions et frais par année)."""

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    ForeignKey,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import ProgramLevel, PublicationStatus, pg_enum

# Format d'année universitaire : 2026-2027
ACADEMIC_YEAR_REGEX = "^[0-9]{4}-[0-9]{4}$"


class Institution(Base):
    __tablename__ = "institutions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    code: Mapped[str] = mapped_column(String(10), unique=True)  # IIT ou ISB
    name: Mapped[str] = mapped_column(String(150))


class Program(Base):
    __tablename__ = "programs"
    __table_args__ = (UniqueConstraint("institution_id", "name"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    institution_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("institutions.id", ondelete="RESTRICT"), index=True
    )
    name: Mapped[str] = mapped_column(String(200))
    level: Mapped[ProgramLevel] = mapped_column(pg_enum(ProgramLevel, "program_level"))
    description: Mapped[str | None] = mapped_column(Text)
    duration_years: Mapped[int | None] = mapped_column(SmallInteger)
    career_outcomes: Mapped[str | None] = mapped_column(Text)
    skills_tags: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))

    institution: Mapped[Institution] = relationship(lazy="joined")


class ProgramYear(Base):
    """Frais et conditions d'admission d'une formation pour une année universitaire."""

    __tablename__ = "program_years"
    __table_args__ = (
        UniqueConstraint("program_id", "academic_year"),
        CheckConstraint(f"academic_year ~ '{ACADEMIC_YEAR_REGEX}'", name="academic_year_format"),
        CheckConstraint("tuition_amount >= 0", name="tuition_non_negative"),
        CheckConstraint("min_average BETWEEN 0 AND 20", name="min_average_range"),
        CheckConstraint(
            "valid_until IS NULL OR valid_from IS NULL OR valid_until >= valid_from",
            name="valid_period_order",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    program_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("programs.id", ondelete="CASCADE"))
    academic_year: Mapped[str] = mapped_column(String(9))  # ex. 2026-2027
    tuition_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))  # TND
    registration_fee: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    min_average: Mapped[Decimal | None] = mapped_column(Numeric(4, 2))
    bac_sections: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    payment_terms: Mapped[str | None] = mapped_column(Text)  # modalités de paiement
    # Seules les offres "published" ET dans leur période de validité sont visibles du public
    status: Mapped[PublicationStatus] = mapped_column(
        pg_enum(PublicationStatus, "publication_status"),
        server_default=PublicationStatus.draft.value,
    )
    valid_from: Mapped[date | None] = mapped_column(Date)
    valid_until: Mapped[date | None] = mapped_column(Date)


class Subject(Base):
    """Matière d'une formation : le programme pédagogique est l'ensemble de ses matières."""

    __tablename__ = "subjects"
    __table_args__ = (
        UniqueConstraint("program_id", "semester", "name"),
        CheckConstraint("semester BETWEEN 1 AND 12", name="semester_range"),
        CheckConstraint("credits IS NULL OR credits >= 0", name="credits_non_negative"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    program_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("programs.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(200))
    semester: Mapped[int] = mapped_column(SmallInteger)
    credits: Mapped[int | None] = mapped_column(SmallInteger)
    description: Mapped[str | None] = mapped_column(Text)
