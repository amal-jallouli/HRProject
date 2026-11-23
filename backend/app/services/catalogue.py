"""Logique métier du catalogue (SA-20 / SA-21).

Règle centrale : le public (candidats, agent IA) ne voit qu'une offre `published` dont la
période de validité couvre la date du jour. Si plusieurs années sont valides, la plus
récente l'emporte.
"""

import uuid
from datetime import date

from fastapi import HTTPException, status
from sqlalchemy import ColumnElement, and_, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Institution, Preregistration, Program, ProgramYear, Recommendation, User
from app.models.enums import ProgramLevel, PublicationStatus, UserRole
from app.schemas.catalogue import (
    ProgramCreate,
    ProgramUpdate,
    ProgramYearCreate,
    ProgramYearUpdate,
)


def _error(code: int, message: str) -> HTTPException:
    return HTTPException(code, message)


# ================================================================== lecture publique
def valid_offer_clauses(today: date) -> list[ColumnElement[bool]]:
    return [
        ProgramYear.status == PublicationStatus.published,
        or_(ProgramYear.valid_from.is_(None), ProgramYear.valid_from <= today),
        or_(ProgramYear.valid_until.is_(None), ProgramYear.valid_until >= today),
    ]


def _escape_like(text: str) -> str:
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _program_filters(
    *,
    q: str | None,
    level: ProgramLevel | None,
    institution: str | None,
    skill: str | None,
) -> list[ColumnElement[bool]]:
    clauses: list[ColumnElement[bool]] = []
    if q:
        pattern = f"%{_escape_like(q.strip())}%"
        clauses.append(
            or_(
                Program.name.ilike(pattern, escape="\\"),
                Program.description.ilike(pattern, escape="\\"),
            )
        )
    if level:
        clauses.append(Program.level == level)
    if institution:
        clauses.append(Institution.code == institution.upper())
    if skill:
        clauses.append(Program.skills_tags.contains([skill.strip().lower()]))
    return clauses


def _offer_filters(
    *, bac_section: str | None, max_tuition: float | None, today: date
) -> list[ColumnElement[bool]]:
    """Filtres portant sur l'offre : le programme doit avoir une offre valide qui les respecte."""
    clauses = [*valid_offer_clauses(today)]
    if bac_section:
        # bac_sections NULL = toutes sections acceptées
        clauses.append(
            or_(
                ProgramYear.bac_sections.is_(None), ProgramYear.bac_sections.contains([bac_section])
            )
        )
    if max_tuition is not None:
        clauses.append(ProgramYear.tuition_amount <= max_tuition)
    return clauses


def current_offers(db: Session, program_ids: list[uuid.UUID], today: date) -> dict:
    """Offre valide la plus récente pour chaque formation donnée."""
    if not program_ids:
        return {}
    rows = db.scalars(
        select(ProgramYear)
        .where(ProgramYear.program_id.in_(program_ids), *valid_offer_clauses(today))
        .order_by(ProgramYear.academic_year)
    ).all()
    return {row.program_id: row for row in rows}  # l'année la plus récente écrase les autres


def list_catalogue(
    db: Session,
    *,
    today: date,
    q: str | None,
    level: ProgramLevel | None,
    institution: str | None,
    skill: str | None,
    bac_section: str | None,
    max_tuition: float | None,
    offset: int,
    size: int,
) -> tuple[list[tuple[Program, ProgramYear | None]], int]:
    where = [
        Program.is_active.is_(True),
        *_program_filters(q=q, level=level, institution=institution, skill=skill),
    ]
    stmt = select(Program).join(Institution, Institution.id == Program.institution_id)
    if bac_section or max_tuition is not None:
        offer_where = _offer_filters(bac_section=bac_section, max_tuition=max_tuition, today=today)
        stmt = stmt.where(
            select(ProgramYear.id)
            .where(ProgramYear.program_id == Program.id, and_(*offer_where))
            .exists()
        )
    stmt = stmt.where(*where)

    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    programs = (
        db.scalars(stmt.order_by(Institution.code, Program.name).offset(offset).limit(size))
        .unique()
        .all()
    )
    offers = current_offers(db, [p.id for p in programs], today)
    return [(p, offers.get(p.id)) for p in programs], total


def get_catalogue_program(
    db: Session, program_id: uuid.UUID, today: date
) -> tuple[Program, ProgramYear | None]:
    program = db.get(Program, program_id)
    if program is None or not program.is_active:
        raise _error(status.HTTP_404_NOT_FOUND, "Formation introuvable")
    return program, current_offers(db, [program.id], today).get(program.id)


def get_valid_offer(
    db: Session, program_id: uuid.UUID, today: date, academic_year: str | None
) -> ProgramYear:
    program = db.get(Program, program_id)
    if program is None or not program.is_active:
        raise _error(status.HTTP_404_NOT_FOUND, "Formation introuvable")
    stmt = select(ProgramYear).where(
        ProgramYear.program_id == program_id, *valid_offer_clauses(today)
    )
    if academic_year:
        stmt = stmt.where(ProgramYear.academic_year == academic_year)
    offer = db.scalars(stmt.order_by(ProgramYear.academic_year.desc())).first()
    if offer is None:
        raise _error(
            status.HTTP_404_NOT_FOUND, "Aucune offre officielle valide pour cette formation"
        )
    return offer


# ================================================================ gestion (responsable)
def _check_scope(user: User, institution_id: uuid.UUID) -> None:
    """Un responsable académique ne gère que sa propre institution ; l'admin gère tout."""
    if user.role == UserRole.academic and user.institution_id != institution_id:
        raise _error(
            status.HTTP_403_FORBIDDEN, "Cette formation appartient à une autre institution"
        )


def get_program_for_user(db: Session, user: User, program_id: uuid.UUID) -> Program:
    program = db.get(Program, program_id)
    if program is None:
        raise _error(status.HTTP_404_NOT_FOUND, "Formation introuvable")
    _check_scope(user, program.institution_id)
    return program


def list_programs_admin(
    db: Session,
    user: User,
    *,
    q: str | None,
    level: ProgramLevel | None,
    institution: str | None,
    skill: str | None,
    is_active: bool | None,
    offset: int,
    size: int,
) -> tuple[list[Program], int]:
    stmt = select(Program).join(Institution, Institution.id == Program.institution_id)
    stmt = stmt.where(*_program_filters(q=q, level=level, institution=institution, skill=skill))
    if user.role == UserRole.academic:
        stmt = stmt.where(Program.institution_id == user.institution_id)
    if is_active is not None:
        stmt = stmt.where(Program.is_active.is_(is_active))
    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    items = (
        db.scalars(stmt.order_by(Institution.code, Program.name).offset(offset).limit(size))
        .unique()
        .all()
    )
    return list(items), total


def _commit(db: Session, conflict_message: str) -> None:
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise _error(status.HTTP_409_CONFLICT, conflict_message) from None


def create_program(db: Session, user: User, data: ProgramCreate) -> Program:
    if user.role == UserRole.academic:
        if data.institution_code and data.institution_code.upper() != _own_code(db, user):
            raise _error(status.HTTP_403_FORBIDDEN, "Vous ne gérez pas cette institution")
        institution_id = user.institution_id
    else:
        if not data.institution_code:
            raise _error(422, "institution_code est obligatoire")
        institution = db.scalar(
            select(Institution).where(Institution.code == data.institution_code.upper())
        )
        if institution is None:
            raise _error(status.HTTP_404_NOT_FOUND, "Institution introuvable")
        institution_id = institution.id

    program = Program(
        institution_id=institution_id,
        **data.model_dump(exclude={"institution_code"}),
    )
    db.add(program)
    _commit(db, "Une formation portant ce nom existe déjà dans cette institution")
    db.refresh(program)
    return program


def _own_code(db: Session, user: User) -> str | None:
    institution = db.get(Institution, user.institution_id) if user.institution_id else None
    return institution.code if institution else None


def update_program(db: Session, user: User, program_id: uuid.UUID, data: ProgramUpdate) -> Program:
    program = get_program_for_user(db, user, program_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(program, field, value)
    _commit(db, "Une formation portant ce nom existe déjà dans cette institution")
    db.refresh(program)
    return program


def delete_program(db: Session, user: User, program_id: uuid.UUID) -> None:
    program = get_program_for_user(db, user, program_id)
    has_published = db.scalar(
        select(ProgramYear.id)
        .where(
            ProgramYear.program_id == program.id,
            ProgramYear.status == PublicationStatus.published,
        )
        .limit(1)
    )
    if has_published:
        raise _error(
            status.HTTP_409_CONFLICT,
            "Formation avec des offres publiées : archivez-les ou désactivez la formation",
        )
    used = db.scalar(
        select(Recommendation.id).where(Recommendation.program_id == program.id).limit(1)
    )
    used = used or db.scalar(
        select(Preregistration.id).where(Preregistration.program_id == program.id).limit(1)
    )
    if used:
        raise _error(
            status.HTTP_409_CONFLICT,
            "Formation utilisée par des recommandations ou préinscriptions : désactivez-la",
        )
    db.delete(program)  # les années non publiées partent avec (ON DELETE CASCADE)
    db.commit()


# ==================================================================== années (frais)
def list_years(db: Session, user: User, program_id: uuid.UUID) -> list[ProgramYear]:
    program = get_program_for_user(db, user, program_id)
    return list(
        db.scalars(
            select(ProgramYear)
            .where(ProgramYear.program_id == program.id)
            .order_by(ProgramYear.academic_year.desc())
        )
    )


def _get_year(db: Session, user: User, program_id: uuid.UUID, academic_year: str) -> ProgramYear:
    program = get_program_for_user(db, user, program_id)
    year = db.scalar(
        select(ProgramYear).where(
            ProgramYear.program_id == program.id, ProgramYear.academic_year == academic_year
        )
    )
    if year is None:
        raise _error(
            status.HTTP_404_NOT_FOUND, "Année universitaire introuvable pour cette formation"
        )
    return year


def get_year(db: Session, user: User, program_id: uuid.UUID, academic_year: str) -> ProgramYear:
    return _get_year(db, user, program_id, academic_year)


def create_year(
    db: Session, user: User, program_id: uuid.UUID, data: ProgramYearCreate
) -> ProgramYear:
    program = get_program_for_user(db, user, program_id)
    year = ProgramYear(program_id=program.id, **data.model_dump())  # statut = draft par défaut
    db.add(year)
    _commit(db, "Cette année universitaire existe déjà pour cette formation")
    db.refresh(year)
    return year


def update_year(
    db: Session, user: User, program_id: uuid.UUID, academic_year: str, data: ProgramYearUpdate
) -> ProgramYear:
    year = _get_year(db, user, program_id, academic_year)
    changes = data.model_dump(exclude_unset=True)
    start = changes.get("valid_from", year.valid_from)
    end = changes.get("valid_until", year.valid_until)
    if start and end and end < start:
        raise _error(
            422,
            "valid_until doit être postérieure ou égale à valid_from",
        )
    if year.status == PublicationStatus.published and start is None:
        raise _error(
            422,
            "Une offre publiée doit garder une date de début de validité",
        )
    for field, value in changes.items():
        setattr(year, field, value)
    db.commit()
    db.refresh(year)
    return year


def delete_year(db: Session, user: User, program_id: uuid.UUID, academic_year: str) -> None:
    year = _get_year(db, user, program_id, academic_year)
    if year.status == PublicationStatus.published:
        raise _error(status.HTTP_409_CONFLICT, "Offre publiée : archivez-la avant de la supprimer")
    db.delete(year)
    db.commit()


def publish_year(db: Session, user: User, program_id: uuid.UUID, academic_year: str) -> ProgramYear:
    year = _get_year(db, user, program_id, academic_year)
    if year.status == PublicationStatus.published:
        raise _error(status.HTTP_409_CONFLICT, "Cette offre est déjà publiée")
    if year.valid_from is None:
        raise _error(
            422,
            "valid_from est obligatoire pour publier une offre",
        )
    year.status = PublicationStatus.published
    db.commit()
    db.refresh(year)
    return year


def archive_year(db: Session, user: User, program_id: uuid.UUID, academic_year: str) -> ProgramYear:
    year = _get_year(db, user, program_id, academic_year)
    if year.status != PublicationStatus.published:
        raise _error(status.HTTP_409_CONFLICT, "Seule une offre publiée peut être archivée")
    year.status = PublicationStatus.archived
    db.commit()
    db.refresh(year)
    return year
