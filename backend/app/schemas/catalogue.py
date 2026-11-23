"""Schémas Pydantic du catalogue (formations, frais, conditions d'admission)."""

import re
import uuid
from datetime import date
from decimal import Decimal
from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.enums import ProgramLevel, PublicationStatus

_YEAR_RE = re.compile(r"^(\d{4})-(\d{4})$")

Money = Annotated[Decimal, Field(ge=0, max_digits=10, decimal_places=2)]
Average = Annotated[Decimal, Field(ge=0, le=20, max_digits=4, decimal_places=2)]
Name = Annotated[str, Field(min_length=2, max_length=200)]


def _clean_tags(tags: list[str] | None) -> list[str] | None:
    if tags is None:
        return None
    cleaned = {t.strip().lower() for t in tags if t.strip()}
    return sorted(cleaned)


def _check_academic_year(value: str) -> str:
    match = _YEAR_RE.match(value)
    if not match or int(match[2]) != int(match[1]) + 1:
        raise ValueError("format attendu : AAAA-AAAA avec années consécutives (ex. 2026-2027)")
    return value


# --------------------------------------------------------------------- institutions
class InstitutionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    name: str


# ------------------------------------------------------------------------ programs
class ProgramBase(BaseModel):
    description: str | None = None
    duration_years: Annotated[int, Field(ge=1, le=10)] | None = None
    career_outcomes: str | None = None
    skills_tags: list[str] | None = None

    @field_validator("skills_tags")
    @classmethod
    def _normalize_tags(cls, v: list[str] | None) -> list[str] | None:
        return _clean_tags(v)


class ProgramCreate(ProgramBase):
    # Optionnel pour un responsable académique (son institution est utilisée) ;
    # obligatoire pour un admin.
    institution_code: Annotated[str, Field(min_length=2, max_length=10)] | None = None
    name: Name
    level: ProgramLevel
    is_active: bool = True


class ProgramUpdate(ProgramBase):
    """PATCH : seuls les champs envoyés sont modifiés."""

    name: Name | None = None
    level: ProgramLevel | None = None
    is_active: bool | None = None

    @model_validator(mode="after")
    def _no_null_on_required(self) -> Self:
        for field in ("name", "level", "is_active"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} ne peut pas être null")
        return self


class ProgramOut(ProgramBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    institution: InstitutionOut
    name: str
    level: ProgramLevel
    is_active: bool


# ------------------------------------------------------------------- program years
class ProgramYearBase(BaseModel):
    tuition_amount: Money
    registration_fee: Money | None = None
    min_average: Average | None = None
    bac_sections: list[str] | None = None
    payment_terms: str | None = None
    valid_from: date | None = None
    valid_until: date | None = None

    @model_validator(mode="after")
    def _period_order(self) -> Self:
        if self.valid_from and self.valid_until and self.valid_until < self.valid_from:
            raise ValueError("valid_until doit être postérieure ou égale à valid_from")
        return self


class ProgramYearCreate(ProgramYearBase):
    academic_year: str

    @field_validator("academic_year")
    @classmethod
    def _year(cls, v: str) -> str:
        return _check_academic_year(v)


class ProgramYearUpdate(BaseModel):
    """PATCH : la période est revérifiée côté service avec les valeurs déjà enregistrées."""

    tuition_amount: Money | None = None
    registration_fee: Money | None = None
    min_average: Average | None = None
    bac_sections: list[str] | None = None
    payment_terms: str | None = None
    valid_from: date | None = None
    valid_until: date | None = None

    @model_validator(mode="after")
    def _checks(self) -> Self:
        if "tuition_amount" in self.model_fields_set and self.tuition_amount is None:
            raise ValueError("tuition_amount ne peut pas être null")
        if self.valid_from and self.valid_until and self.valid_until < self.valid_from:
            raise ValueError("valid_until doit être postérieure ou égale à valid_from")
        return self


class ProgramYearOut(ProgramYearBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    program_id: uuid.UUID
    academic_year: str
    status: PublicationStatus


# --------------------------------------------------------------- public (candidats)
class OfferOut(BaseModel):
    """Offre officielle et valide d'une formation : ce que voient candidats et agent IA."""

    model_config = ConfigDict(from_attributes=True)

    academic_year: str
    tuition_amount: Decimal
    registration_fee: Decimal | None
    min_average: Decimal | None
    bac_sections: list[str] | None
    payment_terms: str | None
    valid_from: date | None
    valid_until: date | None


class CatalogueProgramOut(ProgramOut):
    """Formation + offre valide du jour (None si aucune offre publiée et valide)."""

    offer: OfferOut | None = None


# ------------------------------------------------------------------------ subjects
class SubjectBase(BaseModel):
    name: Name
    semester: Annotated[int, Field(ge=1, le=12)]
    credits: Annotated[int, Field(ge=0, le=60)] | None = None
    description: str | None = None


class SubjectCreate(SubjectBase):
    pass


class SubjectUpdate(BaseModel):
    """PATCH : seuls les champs envoyés sont modifiés."""

    name: Name | None = None
    semester: Annotated[int, Field(ge=1, le=12)] | None = None
    credits: Annotated[int, Field(ge=0, le=60)] | None = None
    description: str | None = None

    @model_validator(mode="after")
    def _no_null_on_required(self) -> Self:
        for field in ("name", "semester"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} ne peut pas être null")
        return self


class SubjectOut(SubjectBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    program_id: uuid.UUID
