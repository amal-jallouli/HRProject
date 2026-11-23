"""Catalogue public : aucune authentification, uniquement des offres officielles valides."""

from datetime import date
from decimal import Decimal

from app.models.enums import ProgramLevel, PublicationStatus

BASE = "/api/v1/catalogue"


def test_institutions_are_public(client, iit, isb):
    response = client.get(f"{BASE}/institutions")
    assert response.status_code == 200
    assert {"IIT", "ISB"} <= {i["code"] for i in response.json()}


def test_list_returns_program_with_valid_offer(client, make_program, make_year, tag):
    program = make_program(skills_tags=["python"])
    make_year(program, payment_terms="3 tranches")
    response = client.get(f"{BASE}/programs", params={"q": tag})
    assert response.status_code == 200
    body = response.json()
    assert (body["total"], body["page"], body["size"]) == (1, 1, 20)
    item = body["items"][0]
    assert item["id"] == str(program.id)
    assert item["institution"]["code"] == "IIT"
    assert item["offer"]["academic_year"] == "2026-2027"
    assert item["offer"]["tuition_amount"] == "7500.00"  # Decimal sérialisé en chaîne
    assert item["offer"]["payment_terms"] == "3 tranches"


def test_draft_and_archived_offers_are_hidden(client, make_program, make_year, tag):
    program = make_program()
    make_year(program, "2026-2027", status=PublicationStatus.draft)
    make_year(program, "2025-2026", status=PublicationStatus.archived)
    item = client.get(f"{BASE}/programs", params={"q": tag}).json()["items"][0]
    assert item["offer"] is None  # la formation reste visible, pas ses frais


def test_expired_and_future_offers_are_hidden(client, make_program, make_year, tag):
    program = make_program()
    make_year(program, "2025-2026", valid_from=date(2025, 6, 1), valid_until=date(2026, 8, 31))
    make_year(program, "2027-2028", valid_from=date(2027, 6, 1), valid_until=date(2028, 8, 31))
    item = client.get(f"{BASE}/programs", params={"q": tag}).json()["items"][0]
    assert item["offer"] is None


def test_validity_boundaries_are_inclusive(client, make_program, make_year, tag):
    program = make_program()
    make_year(program, valid_from=date(2026, 11, 23), valid_until=date(2026, 11, 23))
    assert client.get(f"{BASE}/programs", params={"q": tag}).json()["items"][0]["offer"]


def test_latest_valid_year_wins(client, make_program, make_year, tag):
    program = make_program()
    make_year(program, "2026-2027", tuition_amount=Decimal("7000"))
    make_year(program, "2027-2028", tuition_amount=Decimal("7400"), valid_from=date(2026, 9, 1))
    item = client.get(f"{BASE}/programs", params={"q": tag}).json()["items"][0]
    assert item["offer"]["academic_year"] == "2027-2028"


def test_inactive_program_is_hidden(client, make_program, tag):
    make_program(is_active=False)
    assert client.get(f"{BASE}/programs", params={"q": tag}).json()["total"] == 0


def test_filters(client, make_program, make_year, isb, tag):
    a = make_program("Génie Logiciel", skills_tags=["python", "ia"], level=ProgramLevel.ingenierie)
    b = make_program("Licence Finance", isb, skills_tags=["finance"], level=ProgramLevel.licence)
    make_year(a, tuition_amount=Decimal("8000"), bac_sections=["Mathématiques"])
    make_year(b, tuition_amount=Decimal("5000"), bac_sections=None)

    def ids(**params):
        r = client.get(f"{BASE}/programs", params={"q": tag, **params})
        assert r.status_code == 200
        return {i["id"] for i in r.json()["items"]}

    assert ids() == {str(a.id), str(b.id)}
    assert ids(institution="isb") == {str(b.id)}  # insensible à la casse
    assert ids(level="licence") == {str(b.id)}
    assert ids(skill="IA") == {str(a.id)}
    assert ids(max_tuition=6000) == {str(b.id)}
    assert ids(bac_section="Lettres") == {str(b.id)}  # NULL = toutes sections
    assert ids(bac_section="Mathématiques") == {str(a.id), str(b.id)}


def test_search_escapes_like_wildcards(client, make_program, tag):
    literal = make_program("Génie 100% Logiciel")
    make_program("Génie 100X Logiciel")  # serait trouvé si « % » restait un joker SQL
    under = make_program("Data_Science")
    make_program("DataXScience")  # idem pour « _ »

    def ids(q):
        return {i["id"] for i in client.get(f"{BASE}/programs", params={"q": q}).json()["items"]}

    assert ids(f"100% Logiciel {tag}") == {str(literal.id)}
    assert ids(f"Data_Science {tag}") == {str(under.id)}


def test_pagination(client, make_program, tag):
    for i in range(3):
        make_program(f"Parcours {i}")
    page1 = client.get(f"{BASE}/programs", params={"q": tag, "size": 2}).json()
    page2 = client.get(f"{BASE}/programs", params={"q": tag, "size": 2, "page": 2}).json()
    assert (page1["total"], len(page1["items"]), len(page2["items"])) == (3, 2, 1)


def test_invalid_query_params_return_422(client):
    for params in ({"page": 0}, {"size": 101}, {"level": "nope"}, {"max_tuition": -1}):
        r = client.get(f"{BASE}/programs", params=params)
        assert r.status_code == 422
        assert r.json()["error"]["code"] == "validation_error"


def test_program_detail_and_unknown_id(client, make_program, make_year):
    program = make_program()
    make_year(program)
    r = client.get(f"{BASE}/programs/{program.id}")
    assert r.status_code == 200 and r.json()["offer"]["academic_year"] == "2026-2027"
    missing = client.get(f"{BASE}/programs/00000000-0000-0000-0000-000000000000")
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "http_error"
    assert client.get(f"{BASE}/programs/not-a-uuid").status_code == 422


def test_offer_endpoint(client, make_program, make_year):
    program = make_program()
    make_year(program, "2026-2027")
    make_year(program, "2027-2028", valid_from=date(2026, 9, 1), tuition_amount=Decimal("7900"))
    url = f"{BASE}/programs/{program.id}/offer"
    assert client.get(url).json()["academic_year"] == "2027-2028"
    assert client.get(url, params={"academic_year": "2026-2027"}).json()["academic_year"] == (
        "2026-2027"
    )
    assert client.get(url, params={"academic_year": "2030-2031"}).status_code == 404
    assert client.get(url, params={"academic_year": "abc"}).status_code == 422


def test_offer_404_when_not_official(client, make_program, make_year):
    program = make_program()
    make_year(program, status=PublicationStatus.draft)
    assert client.get(f"{BASE}/programs/{program.id}/offer").status_code == 404


def test_public_endpoints_need_no_auth_but_management_does(client):
    assert client.get(f"{BASE}/programs").status_code == 200
    assert client.get("/api/v1/programs").status_code == 401
