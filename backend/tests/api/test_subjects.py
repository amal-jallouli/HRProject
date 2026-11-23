"""Matières d'une formation : CRUD, accès, validation, lecture publique."""

import pytest

from app.models import Subject
from app.models.enums import UserRole

URL = "/api/v1/programs"
PUBLIC = "/api/v1/catalogue/programs"


@pytest.fixture
def setup(client, academic_iit, auth_headers, make_program):
    return client, make_program(), auth_headers(academic_iit)


def subject(**kw):
    return {"name": "Algorithmique", "semester": 1, "credits": 4, **kw}


def test_create_read_update_delete(setup):
    client, program, h = setup
    r = client.post(f"{URL}/{program.id}/subjects", json=subject(description="Bases"), headers=h)
    assert r.status_code == 201
    sid = r.json()["id"]
    assert r.json()["program_id"] == str(program.id)
    assert client.get(f"{URL}/{program.id}/subjects/{sid}", headers=h).json()["credits"] == 4
    r = client.patch(f"{URL}/{program.id}/subjects/{sid}", json={"credits": 6}, headers=h)
    assert (r.json()["credits"], r.json()["name"]) == (6, "Algorithmique")
    assert client.delete(f"{URL}/{program.id}/subjects/{sid}", headers=h).status_code == 204
    assert client.get(f"{URL}/{program.id}/subjects/{sid}", headers=h).status_code == 404


def test_list_is_ordered_and_filterable(setup):
    client, program, h = setup
    for name, sem in [("Réseaux", 2), ("Algorithmique", 1), ("Analyse", 1)]:
        client.post(
            f"{URL}/{program.id}/subjects", json=subject(name=name, semester=sem), headers=h
        )
    url = f"{URL}/{program.id}/subjects"
    names = [s["name"] for s in client.get(url, headers=h).json()]
    assert names == ["Algorithmique", "Analyse", "Réseaux"]  # par semestre puis nom
    assert [s["name"] for s in client.get(url, params={"semester": 2}, headers=h).json()] == [
        "Réseaux"
    ]
    assert len(client.get(url, params={"q": "ana"}, headers=h).json()) == 1
    assert client.get(url, params={"semester": 13}, headers=h).status_code == 422


@pytest.mark.parametrize(
    "bad",
    [
        {"name": "A"},
        {"name": None},
        {"semester": 0},
        {"semester": 13},
        {"credits": -1},
        {"credits": "abc"},
    ],
)
def test_validation(setup, bad):
    client, program, h = setup
    r = client.post(f"{URL}/{program.id}/subjects", json=subject(**bad), headers=h)
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "validation_error"


def test_required_fields(setup):
    client, program, h = setup
    r = client.post(f"{URL}/{program.id}/subjects", json={}, headers=h)
    assert {d["loc"][-1] for d in r.json()["error"]["details"]} == {"name", "semester"}


def test_patch_rejects_null_on_required(setup):
    client, program, h = setup
    sid = client.post(f"{URL}/{program.id}/subjects", json=subject(), headers=h).json()["id"]
    r = client.patch(f"{URL}/{program.id}/subjects/{sid}", json={"semester": None}, headers=h)
    assert r.status_code == 422


def test_duplicate_is_409_but_same_name_other_semester_ok(setup):
    client, program, h = setup
    url = f"{URL}/{program.id}/subjects"
    assert client.post(url, json=subject(), headers=h).status_code == 201
    assert client.post(url, json=subject(), headers=h).status_code == 409
    assert client.post(url, json=subject(semester=2), headers=h).status_code == 201
    sid = client.post(url, json=subject(name="Autre"), headers=h).json()["id"]
    assert (
        client.patch(f"{url}/{sid}", json={"name": "Algorithmique"}, headers=h).status_code == 409
    )


def test_unknown_ids_and_subject_of_another_program(setup, make_program):
    client, program, h = setup
    sid = client.post(f"{URL}/{program.id}/subjects", json=subject(), headers=h).json()["id"]
    other = make_program("Autre formation")
    ghost = "00000000-0000-0000-0000-000000000000"
    assert client.get(f"{URL}/{ghost}/subjects", headers=h).status_code == 404
    assert client.get(f"{URL}/{program.id}/subjects/{ghost}", headers=h).status_code == 404
    # la matière existe, mais pas sous cette formation
    assert client.get(f"{URL}/{other.id}/subjects/{sid}", headers=h).status_code == 404
    assert client.delete(f"{URL}/{other.id}/subjects/{sid}", headers=h).status_code == 404


def test_access_control(client, academic_isb, make_user, auth_headers, make_program):
    program = make_program()
    url = f"{URL}/{program.id}/subjects"
    assert client.get(url).status_code == 401
    assert client.post(url, json=subject()).status_code == 401
    assert client.get(url, headers=auth_headers(make_user(UserRole.candidate))).status_code == 403
    other = auth_headers(academic_isb)  # autre institution
    assert client.get(url, headers=other).status_code == 403
    assert client.post(url, json=subject(), headers=other).status_code == 403


def test_deleting_program_deletes_its_subjects(setup, db):
    client, program, h = setup
    sid = client.post(f"{URL}/{program.id}/subjects", json=subject(), headers=h).json()["id"]
    assert client.delete(f"{URL}/{program.id}", headers=h).status_code == 204
    db.expire_all()
    assert db.get(Subject, sid) is None


def test_public_list(client, make_program, academic_iit, auth_headers):
    program = make_program()
    h = auth_headers(academic_iit)
    client.post(f"{URL}/{program.id}/subjects", json=subject(), headers=h)
    r = client.get(f"{PUBLIC}/{program.id}/subjects")  # sans authentification
    assert r.status_code == 200 and r.json()[0]["name"] == "Algorithmique"
    assert client.get(f"{PUBLIC}/{program.id}/subjects", params={"semester": 2}).json() == []
    ghost = "00000000-0000-0000-0000-000000000000"
    assert client.get(f"{PUBLIC}/{ghost}/subjects").status_code == 404


def test_public_list_hides_inactive_program(client, make_program, academic_iit, auth_headers):
    program = make_program(is_active=False)
    client.post(f"{URL}/{program.id}/subjects", json=subject(), headers=auth_headers(academic_iit))
    assert client.get(f"{PUBLIC}/{program.id}/subjects").status_code == 404
