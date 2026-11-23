"""Frais, modalités de paiement, conditions d'admission, publication et validité (SA-21)."""

from datetime import date

import pytest

URL = "/api/v1/programs"
OFFER = "/api/v1/catalogue/programs"


@pytest.fixture
def setup(client, academic_iit, auth_headers, make_program):
    program = make_program()
    return client, program, auth_headers(academic_iit)


def body(**kw):
    return {"academic_year": "2026-2027", "tuition_amount": "7500", **kw}


def test_create_year_is_draft_and_not_public(setup):
    client, program, h = setup
    r = client.post(
        f"{URL}/{program.id}/years",
        json=body(
            registration_fee="150",
            min_average="12.5",
            bac_sections=["Mathématiques"],
            payment_terms="3 tranches",
            valid_from="2026-06-01",
            valid_until="2027-08-31",
        ),
        headers=h,
    )
    assert r.status_code == 201
    assert r.json()["status"] == "draft"
    assert r.json()["payment_terms"] == "3 tranches"
    assert client.get(f"{OFFER}/{program.id}/offer").status_code == 404  # pas encore officiel


def test_publish_makes_offer_public_then_archive_hides_it(setup):
    client, program, h = setup
    client.post(f"{URL}/{program.id}/years", json=body(valid_from="2026-06-01"), headers=h)
    r = client.post(f"{URL}/{program.id}/years/2026-2027/publish", headers=h)
    assert r.status_code == 200 and r.json()["status"] == "published"
    assert client.get(f"{OFFER}/{program.id}/offer").json()["tuition_amount"] == "7500.00"

    r = client.post(f"{URL}/{program.id}/years/2026-2027/archive", headers=h)
    assert r.json()["status"] == "archived"
    assert client.get(f"{OFFER}/{program.id}/offer").status_code == 404


def test_publish_requires_valid_from(setup):
    client, program, h = setup
    client.post(f"{URL}/{program.id}/years", json=body(), headers=h)
    assert client.post(f"{URL}/{program.id}/years/2026-2027/publish", headers=h).status_code == 422


def test_publish_and_archive_state_rules(setup):
    client, program, h = setup
    client.post(f"{URL}/{program.id}/years", json=body(valid_from="2026-06-01"), headers=h)
    base = f"{URL}/{program.id}/years/2026-2027"
    assert client.post(f"{base}/archive", headers=h).status_code == 409  # brouillon
    assert client.post(f"{base}/publish", headers=h).status_code == 200
    assert client.post(f"{base}/publish", headers=h).status_code == 409  # déjà publiée
    assert client.post(f"{base}/archive", headers=h).status_code == 200
    assert client.post(f"{base}/publish", headers=h).status_code == 200  # republication possible


def test_published_offer_outside_validity_is_not_public(setup):
    client, program, h = setup
    client.post(
        f"{URL}/{program.id}/years",
        json=body(
            valid_from="2027-01-01", valid_until="2027-12-31"
        ),  # commence après « aujourd'hui »
        headers=h,
    )
    client.post(f"{URL}/{program.id}/years/2026-2027/publish", headers=h)
    assert client.get(f"{OFFER}/{program.id}/offer").status_code == 404


@pytest.mark.parametrize(
    "bad",
    [
        {"academic_year": "2026"},
        {"academic_year": "2026-2028"},  # années non consécutives
        {"academic_year": "26-27"},
        {"tuition_amount": "-1"},
        {"tuition_amount": "abc"},
        {"tuition_amount": "1.234"},
        {"registration_fee": "-5"},
        {"min_average": "21"},
        {"min_average": "-1"},
        {"valid_from": "2027-01-01", "valid_until": "2026-01-01"},
        {"valid_from": "pas-une-date"},
    ],
)
def test_create_year_validation(setup, bad):
    client, program, h = setup
    r = client.post(f"{URL}/{program.id}/years", json=body(**bad), headers=h)
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "validation_error"


def test_required_fields(setup):
    client, program, h = setup
    r = client.post(f"{URL}/{program.id}/years", json={}, headers=h)
    missing = {d["loc"][-1] for d in r.json()["error"]["details"]}
    assert missing == {"academic_year", "tuition_amount"}


def test_duplicate_year_is_409(setup):
    client, program, h = setup
    assert client.post(f"{URL}/{program.id}/years", json=body(), headers=h).status_code == 201
    assert client.post(f"{URL}/{program.id}/years", json=body(), headers=h).status_code == 409


def test_unknown_program_or_year(setup):
    client, program, h = setup
    ghost = "00000000-0000-0000-0000-000000000000"
    assert client.post(f"{URL}/{ghost}/years", json=body(), headers=h).status_code == 404
    assert client.get(f"{URL}/{program.id}/years/2030-2031", headers=h).status_code == 404
    assert client.delete(f"{URL}/{program.id}/years/2030-2031", headers=h).status_code == 404
    assert client.post(f"{URL}/{program.id}/years/2030-2031/publish", headers=h).status_code == 404


def test_list_and_get_years(setup):
    client, program, h = setup
    for y in ("2026-2027", "2027-2028"):
        client.post(f"{URL}/{program.id}/years", json=body(academic_year=y), headers=h)
    listing = client.get(f"{URL}/{program.id}/years", headers=h).json()
    assert [y["academic_year"] for y in listing] == ["2027-2028", "2026-2027"]
    assert client.get(f"{URL}/{program.id}/years/2026-2027", headers=h).json()["program_id"] == (
        str(program.id)
    )


def test_update_year(setup):
    client, program, h = setup
    client.post(f"{URL}/{program.id}/years", json=body(payment_terms="a"), headers=h)
    r = client.patch(
        f"{URL}/{program.id}/years/2026-2027",
        json={"tuition_amount": "8000", "min_average": "13"},
        headers=h,
    )
    assert r.status_code == 200
    assert (r.json()["tuition_amount"], r.json()["payment_terms"]) == ("8000.00", "a")


def test_update_period_is_checked_against_stored_values(setup):
    client, program, h = setup
    client.post(f"{URL}/{program.id}/years", json=body(valid_from="2026-06-01"), headers=h)
    url = f"{URL}/{program.id}/years/2026-2027"
    assert client.patch(url, json={"valid_until": "2026-01-01"}, headers=h).status_code == 422
    assert client.patch(url, json={"tuition_amount": None}, headers=h).status_code == 422


def test_published_offer_keeps_a_start_date(setup):
    client, program, h = setup
    client.post(f"{URL}/{program.id}/years", json=body(valid_from="2026-06-01"), headers=h)
    url = f"{URL}/{program.id}/years/2026-2027"
    client.post(f"{url}/publish", headers=h)
    assert client.patch(url, json={"valid_from": None}, headers=h).status_code == 422


def test_delete_year_rules(setup):
    client, program, h = setup
    client.post(f"{URL}/{program.id}/years", json=body(valid_from="2026-06-01"), headers=h)
    url = f"{URL}/{program.id}/years/2026-2027"
    client.post(f"{url}/publish", headers=h)
    assert client.delete(url, headers=h).status_code == 409  # publiée
    client.post(f"{url}/archive", headers=h)
    assert client.delete(url, headers=h).status_code == 204
    assert client.get(url, headers=h).status_code == 404


def test_years_access_control(
    client, academic_isb, admin, make_user, auth_headers, make_program, make_year
):
    from app.models.enums import UserRole

    program = make_program()
    make_year(program, status="draft")
    url = f"{URL}/{program.id}/years"
    assert client.get(url).status_code == 401
    assert client.get(url, headers=auth_headers(make_user(UserRole.candidate))).status_code == 403
    other = auth_headers(academic_isb)
    assert client.get(url, headers=other).status_code == 403
    assert client.post(url, json=body(academic_year="2030-2031"), headers=other).status_code == 403
    assert client.post(f"{url}/2026-2027/publish", headers=other).status_code == 403
    assert client.get(url, headers=auth_headers(admin)).status_code == 200


def test_valid_from_date_type_roundtrip(setup):
    client, program, h = setup
    r = client.post(f"{URL}/{program.id}/years", json=body(valid_from="2026-06-01"), headers=h)
    assert date.fromisoformat(r.json()["valid_from"]) == date(2026, 6, 1)
