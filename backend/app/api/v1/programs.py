"""Gestion du catalogue (SA-20) et des frais / conditions par année (SA-21).

Réservé aux responsables académiques (leur institution uniquement) et aux admins.
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Query, Response, status

from app.api.deps import CatalogueManager, DbSession, Pagination
from app.models import Program, ProgramYear
from app.models.enums import ProgramLevel
from app.schemas.catalogue import (
    ProgramCreate,
    ProgramOut,
    ProgramUpdate,
    ProgramYearCreate,
    ProgramYearOut,
    ProgramYearUpdate,
)
from app.schemas.common import Page
from app.services import catalogue as service

router = APIRouter(prefix="/programs", tags=["formations (gestion)"])


@router.get("", response_model=Page[ProgramOut], summary="Lister / rechercher mes formations")
def list_programs(
    db: DbSession,
    user: CatalogueManager,
    pagination: Pagination,
    q: Annotated[str | None, Query(max_length=100)] = None,
    level: ProgramLevel | None = None,
    institution: Annotated[str | None, Query(max_length=10)] = None,
    skill: Annotated[str | None, Query(max_length=50)] = None,
    is_active: bool | None = None,
) -> Page[ProgramOut]:
    items, total = service.list_programs_admin(
        db,
        user,
        q=q,
        level=level,
        institution=institution,
        skill=skill,
        is_active=is_active,
        offset=pagination.offset,
        size=pagination.size,
    )
    return Page(items=items, total=total, page=pagination.page, size=pagination.size)


@router.post("", response_model=ProgramOut, status_code=status.HTTP_201_CREATED)
def create_program(body: ProgramCreate, db: DbSession, user: CatalogueManager) -> Program:
    return service.create_program(db, user, body)


@router.get("/{program_id}", response_model=ProgramOut)
def get_program(program_id: uuid.UUID, db: DbSession, user: CatalogueManager) -> Program:
    return service.get_program_for_user(db, user, program_id)


@router.patch("/{program_id}", response_model=ProgramOut)
def update_program(
    program_id: uuid.UUID, body: ProgramUpdate, db: DbSession, user: CatalogueManager
) -> Program:
    return service.update_program(db, user, program_id, body)


@router.delete("/{program_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_program(program_id: uuid.UUID, db: DbSession, user: CatalogueManager) -> Response:
    service.delete_program(db, user, program_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ------------------------------------------------------------ frais / conditions par année
@router.get("/{program_id}/years", response_model=list[ProgramYearOut])
def list_years(program_id: uuid.UUID, db: DbSession, user: CatalogueManager) -> list[ProgramYear]:
    return service.list_years(db, user, program_id)


@router.post(
    "/{program_id}/years", response_model=ProgramYearOut, status_code=status.HTTP_201_CREATED
)
def create_year(
    program_id: uuid.UUID, body: ProgramYearCreate, db: DbSession, user: CatalogueManager
) -> ProgramYear:
    return service.create_year(db, user, program_id, body)


@router.get("/{program_id}/years/{academic_year}", response_model=ProgramYearOut)
def get_year(
    program_id: uuid.UUID, academic_year: str, db: DbSession, user: CatalogueManager
) -> ProgramYear:
    return service.get_year(db, user, program_id, academic_year)


@router.patch("/{program_id}/years/{academic_year}", response_model=ProgramYearOut)
def update_year(
    program_id: uuid.UUID,
    academic_year: str,
    body: ProgramYearUpdate,
    db: DbSession,
    user: CatalogueManager,
) -> ProgramYear:
    return service.update_year(db, user, program_id, academic_year, body)


@router.delete("/{program_id}/years/{academic_year}", status_code=status.HTTP_204_NO_CONTENT)
def delete_year(
    program_id: uuid.UUID, academic_year: str, db: DbSession, user: CatalogueManager
) -> Response:
    service.delete_year(db, user, program_id, academic_year)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{program_id}/years/{academic_year}/publish", response_model=ProgramYearOut)
def publish_year(
    program_id: uuid.UUID, academic_year: str, db: DbSession, user: CatalogueManager
) -> ProgramYear:
    return service.publish_year(db, user, program_id, academic_year)


@router.post("/{program_id}/years/{academic_year}/archive", response_model=ProgramYearOut)
def archive_year(
    program_id: uuid.UUID, academic_year: str, db: DbSession, user: CatalogueManager
) -> ProgramYear:
    return service.archive_year(db, user, program_id, academic_year)
