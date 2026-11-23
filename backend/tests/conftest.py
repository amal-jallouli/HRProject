"""Fixtures communes : session PostgreSQL annulée après chaque test, client, utilisateurs.

Les tests tournent sur la base de développement mais dans une transaction qui est
TOUJOURS annulée : les données de démonstration ne sont jamais modifiées. Si PostgreSQL
n'est pas joignable, les tests qui en ont besoin sont ignorés.
"""

import uuid
from collections.abc import Callable, Iterator
from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_optional, get_db, get_today  # noqa: F401
from app.db.session import engine
from app.main import app
from app.models import Institution, Program, ProgramYear, User
from app.models.enums import ProgramLevel, PublicationStatus, UserRole

TODAY = date(2026, 11, 23)


@pytest.fixture
def db() -> Iterator[Session]:
    try:
        connection = engine.connect()
        connection.execute(text("SELECT 1 FROM program_years LIMIT 1"))
    except Exception:  # noqa: BLE001
        pytest.skip("PostgreSQL indisponible ou migrations non appliquées (make db-upgrade)")
    connection.rollback()
    transaction = connection.begin()
    # Chaque commit() libère un SAVEPOINT ; un rollback() (ex. erreur 409) n'annule donc que
    # ce qui a suivi le dernier commit, comme une requête réelle avec sa propre session.
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def client(db: Session) -> Iterator[TestClient]:
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_today] = lambda: TODAY
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def tag() -> str:
    """Suffixe unique : isole les données du test de celles de la démo (recherche `q`)."""
    return uuid.uuid4().hex[:8]


def _institution(db: Session, code: str) -> Institution:
    inst = db.scalar(select(Institution).where(Institution.code == code))
    if inst is None:
        inst = Institution(code=code, name=f"Institution {code}")
        db.add(inst)
        db.commit()
    return inst


@pytest.fixture
def iit(db: Session) -> Institution:
    return _institution(db, "IIT")


@pytest.fixture
def isb(db: Session) -> Institution:
    return _institution(db, "ISB")


@pytest.fixture
def make_user(db: Session) -> Callable[..., User]:
    def _make(role: UserRole, institution: Institution | None = None) -> User:
        user = User(
            email=f"{role.value}-{uuid.uuid4().hex[:8]}@test.local",
            password_hash="x",
            role=role,
            institution_id=institution.id if institution else None,
        )
        db.add(user)
        db.commit()
        return user

    return _make


@pytest.fixture
def auth_headers() -> Callable[[User], dict[str, str]]:
    """Seul endroit à adapter quand SA-28 (vraie authentification) sera livrée."""
    return lambda user: {"X-User-Email": user.email}


@pytest.fixture
def academic_iit(make_user, iit) -> User:
    return make_user(UserRole.academic, iit)


@pytest.fixture
def academic_isb(make_user, isb) -> User:
    return make_user(UserRole.academic, isb)


@pytest.fixture
def admin(make_user) -> User:
    return make_user(UserRole.admin)


@pytest.fixture
def make_program(db: Session, iit: Institution, tag: str) -> Callable[..., Program]:
    def _make(
        name: str = "Génie Logiciel", institution: Institution | None = None, **kw
    ) -> Program:
        program = Program(
            institution_id=(institution or iit).id,
            name=f"{name} {tag}",
            level=kw.pop("level", ProgramLevel.ingenierie),
            **kw,
        )
        db.add(program)
        db.commit()
        return program

    return _make


@pytest.fixture
def make_year(db: Session) -> Callable[..., ProgramYear]:
    def _make(program: Program, academic_year: str = "2026-2027", **kw) -> ProgramYear:
        kw.setdefault("tuition_amount", Decimal("7500"))
        kw.setdefault("status", PublicationStatus.published)
        kw.setdefault("valid_from", date(2026, 6, 1))
        kw.setdefault("valid_until", date(2027, 8, 31))
        year = ProgramYear(program_id=program.id, academic_year=academic_year, **kw)
        db.add(year)
        db.commit()
        return year

    return _make
