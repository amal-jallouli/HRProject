"""Catalogue PUBLIC : formations et offres officielles valides (aucune authentification)."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Query
from sqlalchemy import select

from app.api.deps import DbSession, Pagination, Today
from app.models import Institution, Subject
from app.models.enums import ProgramLevel
from app.schemas.catalogue import CatalogueProgramOut, InstitutionOut, OfferOut, SubjectOut
from app.schemas.common import Page
from app.services import catalogue as service

router = APIRouter(prefix="/catalogue", tags=["catalogue (public)"])


@router.get("/institutions", response_model=list[InstitutionOut], summary="Institutions")
def list_institutions(db: DbSession) -> list[Institution]:
    return list(db.scalars(select(Institution).order_by(Institution.code)))


@router.get(
    "/programs",
    response_model=Page[CatalogueProgramOut],
    summary="Rechercher les formations (avec leur offre officielle valide)",
)
def list_programs(
    db: DbSession,
    today: Today,
    pagination: Pagination,
    q: Annotated[
        str | None, Query(max_length=100, description="Mot-clé (nom, description)")
    ] = None,
    level: ProgramLevel | None = None,
    institution: Annotated[str | None, Query(max_length=10, description="IIT ou ISB")] = None,
    skill: Annotated[str | None, Query(max_length=50)] = None,
    bac_section: Annotated[str | None, Query(max_length=60)] = None,
    max_tuition: Annotated[float | None, Query(ge=0)] = None,
) -> Page[CatalogueProgramOut]:
    rows, total = service.list_catalogue(
        db,
        today=today,
        q=q,
        level=level,
        institution=institution,
        skill=skill,
        bac_section=bac_section,
        max_tuition=max_tuition,
        offset=pagination.offset,
        size=pagination.size,
    )
    items = [_to_out(program, offer) for program, offer in rows]
    return Page(items=items, total=total, page=pagination.page, size=pagination.size)


@router.get("/programs/{program_id}", response_model=CatalogueProgramOut, summary="Détail")
def get_program(program_id: uuid.UUID, db: DbSession, today: Today) -> CatalogueProgramOut:
    program, offer = service.get_catalogue_program(db, program_id, today)
    return _to_out(program, offer)


@router.get(
    "/programs/{program_id}/offer",
    response_model=OfferOut,
    summary="Frais, modalités de paiement et conditions officiels et valides",
)
def get_offer(
    program_id: uuid.UUID,
    db: DbSession,
    today: Today,
    academic_year: Annotated[str | None, Query(pattern=r"^\d{4}-\d{4}$")] = None,
):
    return service.get_valid_offer(db, program_id, today, academic_year)


@router.get(
    "/programs/{program_id}/subjects",
    response_model=list[SubjectOut],
    summary="Matières (programme pédagogique) d'une formation",
)
def list_subjects(
    program_id: uuid.UUID,
    db: DbSession,
    semester: Annotated[int | None, Query(ge=1, le=12)] = None,
    q: Annotated[str | None, Query(max_length=100)] = None,
) -> list[Subject]:
    return service.list_public_subjects(db, program_id, semester, q)


def _to_out(program, offer) -> CatalogueProgramOut:
    out = CatalogueProgramOut.model_validate(program)
    out.offer = OfferOut.model_validate(offer) if offer else None
    return out
