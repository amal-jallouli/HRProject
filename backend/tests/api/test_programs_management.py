"""Gestion des formations : CRUD, accès par rôle, validation, relations."""

from decimal import Decimal

import pytest

from app.models import Candidate, Recommendation
from app.models.enums import PublicationStatus, UserRole

URL = "/api/v1/programs"


def payload(tag, **kw):
    return {"name": f"Cyber {tag}", "level": "ingenierie", **kw}


# ------------------------------------------------------------------ accès
def test_anonymous_gets_401(client, make_program):
    program = make_program()
    assert client.get(URL).status_code == 401
    assert client.post(URL, json={}).status_code == 401
    assert client.patch(f"{URL}/{program.id}", json={}).status_code == 401
    assert client.delete(f"{URL}/{program.id}").status_code == 401


def test_unknown_email_gets_401(client):
    assert client.get(URL, headers={"X-User-Email": "ghost@test.local"}).status_code == 401


@pytest.mark.parametrize("role", [UserRole.candidate, UserRole.interviewer])
def test_other_roles_get_403(client, make_user, auth_headers, make_program, role):
    user = make_user(role)
    program = make_program()
    headers = auth_headers(user)
    assert client.get(URL, headers=headers).status_code == 403
    assert client.delete(f"{URL}/{program.id}", headers=headers).status_code == 403


def test_header_is_ignored_in_production(client, monkeypatch, academic_iit, auth_headers):
    from app.core.config import settings

    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    assert client.get(URL, headers=auth_headers(academic_iit)).status_code == 401


def test_academic_cannot_touch_other_institution(client, academic_isb, auth_headers, make_program):
    program = make_program()  # IIT
    h = auth_headers(academic_isb)
    assert client.get(f"{URL}/{program.id}", headers=h).status_code == 403
    assert (
        client.patch(f"{URL}/{program.id}", json={"name": "Nom valide"}, headers=h).status_code
        == 403
    )
    assert client.delete(f"{URL}/{program.id}", headers=h).status_code == 403
    assert client.get(f"{URL}/{program.id}/years", headers=h).status_code == 403
    r = client.post(URL, json=payload("x", institution_code="IIT"), headers=h)
    assert r.status_code == 403


def test_academic_list_is_scoped_to_own_institution(
    client, academic_isb, admin, auth_headers, make_program, isb, tag
):
    mine, other = make_program("Master", isb), make_program("Licence")
    r = client.get(URL, params={"q": tag}, headers=auth_headers(academic_isb))
    assert {i["id"] for i in r.json()["items"]} == {str(mine.id)}
    r = client.get(URL, params={"q": tag}, headers=auth_headers(admin))
    assert {i["id"] for i in r.json()["items"]} == {str(mine.id), str(other.id)}


# ------------------------------------------------------------------- CRUD
def test_create_read_update_delete(client, academic_iit, auth_headers, tag):
    h = auth_headers(academic_iit)
    r = client.post(
        URL,
        json=payload(tag, skills_tags=[" Python ", "IA", "python"], duration_years=5),
        headers=h,
    )
    assert r.status_code == 201
    created = r.json()
    assert created["institution"]["code"] == "IIT"  # déduite du responsable
    assert created["skills_tags"] == ["ia", "python"]  # normalisé, sans doublon
    assert created["is_active"] is True

    pid = created["id"]
    assert client.get(f"{URL}/{pid}", headers=h).json()["name"] == f"Cyber {tag}"

    r = client.patch(
        f"{URL}/{pid}", json={"description": "Nouvelle", "is_active": False}, headers=h
    )
    assert r.status_code == 200
    assert (r.json()["description"], r.json()["is_active"]) == ("Nouvelle", False)
    assert r.json()["name"] == f"Cyber {tag}"  # champ non envoyé : inchangé

    assert client.delete(f"{URL}/{pid}", headers=h).status_code == 204
    assert client.get(f"{URL}/{pid}", headers=h).status_code == 404


def test_admin_must_give_institution_code(client, admin, auth_headers, tag, isb):
    h = auth_headers(admin)
    assert client.post(URL, json=payload(tag), headers=h).status_code == 422
    assert client.post(URL, json=payload(tag, institution_code="XXX"), headers=h).status_code == 404
    r = client.post(URL, json=payload(tag, institution_code="isb"), headers=h)
    assert r.status_code == 201 and r.json()["institution"]["code"] == "ISB"


@pytest.mark.parametrize(
    "bad",
    [
        {"name": "A"},
        {"level": "inconnu"},
        {"duration_years": 0},
        {"duration_years": 11},
        {"name": None},
    ],
)
def test_create_validation(client, academic_iit, auth_headers, tag, bad):
    body = {**payload(tag), **bad}
    r = client.post(URL, json=body, headers=auth_headers(academic_iit))
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "validation_error"


def test_required_fields(client, academic_iit, auth_headers):
    r = client.post(URL, json={}, headers=auth_headers(academic_iit))
    assert r.status_code == 422
    missing = {d["loc"][-1] for d in r.json()["error"]["details"]}
    assert {"name", "level"} <= missing


def test_patch_rejects_null_on_required_fields(client, academic_iit, auth_headers, make_program):
    program = make_program()
    r = client.patch(
        f"{URL}/{program.id}", json={"level": None}, headers=auth_headers(academic_iit)
    )
    assert r.status_code == 422


def test_duplicate_name_is_409(client, academic_iit, auth_headers, make_program, tag):
    make_program("Cyber")
    h = auth_headers(academic_iit)
    assert client.post(URL, json=payload(tag), headers=h).status_code == 409
    other = client.post(URL, json=payload(f"{tag} bis"), headers=h).json()
    r = client.patch(f"{URL}/{other['id']}", json={"name": f"Cyber {tag}"}, headers=h)
    assert r.status_code == 409


def test_same_name_allowed_in_other_institution(
    client, admin, auth_headers, make_program, tag, isb
):
    make_program("Cyber")
    r = client.post(URL, json=payload(tag, institution_code="ISB"), headers=auth_headers(admin))
    assert r.status_code == 201


def test_unknown_or_malformed_id(client, academic_iit, auth_headers):
    h = auth_headers(academic_iit)
    assert client.get(f"{URL}/00000000-0000-0000-0000-000000000000", headers=h).status_code == 404
    assert client.get(f"{URL}/abc", headers=h).status_code == 422


def test_list_filters_and_inactive(client, academic_iit, auth_headers, make_program, tag):
    make_program("Actif")
    inactive = make_program("Inactif", is_active=False)
    h = auth_headers(academic_iit)
    r = client.get(URL, params={"q": tag, "is_active": False}, headers=h)
    assert [i["id"] for i in r.json()["items"]] == [str(inactive.id)]  # le responsable le voit
    assert client.get(URL, params={"q": tag}, headers=h).json()["total"] == 2


# ----------------------------------------------------------- relations / suppression
def test_delete_cascades_unpublished_years(
    client, academic_iit, auth_headers, make_program, make_year, db
):
    from app.models import ProgramYear

    program = make_program()
    year = make_year(program, status=PublicationStatus.draft)
    year_id = year.id
    assert (
        client.delete(f"{URL}/{program.id}", headers=auth_headers(academic_iit)).status_code == 204
    )
    db.expire_all()
    assert db.get(ProgramYear, year_id) is None


def test_delete_blocked_by_published_year(
    client, academic_iit, auth_headers, make_program, make_year
):
    program = make_program()
    make_year(program)
    r = client.delete(f"{URL}/{program.id}", headers=auth_headers(academic_iit))
    assert r.status_code == 409


def test_delete_blocked_by_recommendation(client, academic_iit, auth_headers, make_program, db):
    program = make_program()
    candidate = Candidate()
    db.add(candidate)
    db.commit()
    db.add(Recommendation(candidate_id=candidate.id, program_id=program.id))
    db.commit()
    r = client.delete(f"{URL}/{program.id}", headers=auth_headers(academic_iit))
    assert r.status_code == 409
    assert client.get(f"{URL}/{program.id}", headers=auth_headers(academic_iit)).status_code == 200


def test_decimal_precision_roundtrip(client, academic_iit, auth_headers, make_program):
    program = make_program()
    h = auth_headers(academic_iit)
    r = client.post(
        f"{URL}/{program.id}/years",
        json={"academic_year": "2026-2027", "tuition_amount": "7500.50"},
        headers=h,
    )
    assert r.status_code == 201 and Decimal(r.json()["tuition_amount"]) == Decimal("7500.50")
