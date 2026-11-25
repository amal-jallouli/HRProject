"""SA-38 : tests du dialogue avec le LLM à travers l'API (mémoire de session, SA-37).

Le LLM est simulé (Ollama n'est pas nécessaire). Comme les tests des sessions visiteurs,
ces tests utilisent la base Redis n°15, vidée avant et après chaque test ; ils sont ignorés
si Redis n'est pas joignable.
"""

import json
from collections.abc import Iterator

import pytest
from app.api.v1.llm import get_llm_client
from app.core.config import settings
from app.core.exceptions import AppError
from app.core.redis_client import get_redis
from app.main import app
from app.services import llm as service
from app.services.llm_prompt import MESSAGE_REPLI
from fastapi.testclient import TestClient
from redis import Redis

URL = "/api/v1/llm/conversation"
SESSIONS = "/api/v1/visitor-sessions"


class FakeLLMClient(service.LLMClient):
    """Renvoie les sorties préparées, dans l'ordre, et garde les messages reçus."""

    def __init__(self) -> None:
        super().__init__()
        self.sorties: list[str | Exception] = []
        self.appels: list[list[dict[str, str]]] = []

    def chat(self, messages: list[dict[str, str]]) -> str:
        self.appels.append(messages)
        sortie = self.sorties.pop(0)
        if isinstance(sortie, Exception):
            raise sortie
        return sortie


def sortie(reponse: str, intention: str = "INFO_FORMATION", **profil) -> str:
    return json.dumps(
        {"langue": "fr", "intention": intention, "profil": profil, "reponse": reponse},
        ensure_ascii=False,
    )


@pytest.fixture
def redis_test() -> Iterator[Redis]:
    client = Redis.from_url(settings.REDIS_URL, db=15, decode_responses=True)
    try:
        client.ping()
    except Exception:  # noqa: BLE001
        pytest.skip("Redis indisponible (docker compose up -d)")
    client.flushdb()
    yield client
    client.flushdb()


@pytest.fixture
def api(redis_test: Redis) -> Iterator[tuple[TestClient, FakeLLMClient, dict[str, str]]]:
    fake = FakeLLMClient()
    app.dependency_overrides[get_redis] = lambda: redis_test
    app.dependency_overrides[get_llm_client] = lambda: fake
    client = TestClient(app)
    token = client.post(SESSIONS).json()["token"]
    yield client, fake, {"X-Visitor-Token": token}
    app.dependency_overrides.clear()


def memoire(client: TestClient, headers: dict[str, str]) -> list[dict]:
    return client.get(f"{SESSIONS}/me/memory", headers=headers).json()["messages"]


# ------------------------------------------------------------------ échanges successifs
def test_plusieurs_echanges_successifs_en_francais(api) -> None:
    client, fake, headers = api
    fake.sorties = [
        sortie("Bonjour ! Quel est ton bac ?", "SALUTATION"),
        sortie("D'accord, quelle formation t'intéresse ?", "PROFIL", section_bac="mathématiques"),
        sortie("La licence est plus courte, la prépa plus théorique.", "COMPARAISON"),
    ]
    questions = ["Bonjour", "J'ai un bac maths", "Prépa ou licence ?"]
    for question in questions:
        r = client.post(URL, json={"message": question}, headers=headers)
        assert r.status_code == 200
        assert r.json()["repli"] is False

    messages = memoire(client, headers)
    assert [m["role"] for m in messages] == ["user", "assistant"] * 3
    assert [m["content"] for m in messages if m["role"] == "user"] == questions


# ------------------------------------------------------------------ conservation du contexte
def test_le_contexte_est_transmis_au_modele(api) -> None:
    client, fake, headers = api
    fake.sorties = [
        sortie("Les frais de l'IIT sont à confirmer auprès du service des admissions."),
        sortie("Pour l'ISB, cette information est aussi à vérifier auprès des admissions."),
    ]
    client.post(URL, json={"message": "Quels sont les frais à l'IIT ?"}, headers=headers)
    client.post(URL, json={"message": "Et pour l'ISB ?"}, headers=headers)

    envoyes = fake.appels[1]
    assert envoyes[0]["role"] == "system"
    assert {"role": "user", "content": "Quels sont les frais à l'IIT ?"} in envoyes
    assert any(m["role"] == "assistant" and "IIT" in m["content"] for m in envoyes)
    assert envoyes[-1] == {"role": "user", "content": "Et pour l'ISB ?"}


def test_la_fiche_du_visiteur_est_transmise(api) -> None:
    client, fake, headers = api
    client.patch(
        f"{SESSIONS}/me/memory/facts",
        json={"bac_section": "Mathématiques", "average_grade": 14},
        headers=headers,
    )
    fake.sorties = [sortie("Avec un bac maths, plusieurs parcours sont possibles.", "ORIENTATION")]
    client.post(URL, json={"message": "Que me conseilles-tu ?"}, headers=headers)

    contexte = fake.appels[0][1]["content"]
    assert contexte.startswith("Informations déjà connues")
    assert "Mathématiques" in contexte and "14" in contexte


def test_seuls_les_messages_recents_sont_transmis(api, monkeypatch) -> None:
    client, fake, headers = api
    monkeypatch.setattr(settings, "LLM_HISTORY_MAX_MESSAGES", 4)
    fake.sorties = [sortie(f"réponse {i}") for i in range(4)]
    for i in range(4):
        client.post(URL, json={"message": f"question {i}"}, headers=headers)

    # prompt système + 4 messages récents + question actuelle
    assert len(fake.appels[-1]) == 1 + 4 + 1
    assert {"role": "user", "content": "question 0"} not in fake.appels[-1]


def test_les_sessions_ne_partagent_pas_leur_contexte(api) -> None:
    client, fake, headers = api
    autre = {"X-Visitor-Token": client.post(SESSIONS).json()["token"]}
    fake.sorties = [sortie("ok"), sortie("ok")]
    client.post(URL, json={"message": "Je m'appelle Sara"}, headers=headers)
    client.post(URL, json={"message": "Bonjour"}, headers=autre)

    assert len(fake.appels[1]) == 2  # prompt système + question, aucun historique


# ------------------------------------------------------------------ instructions
def test_instructions_contre_les_informations_non_verifiees(api) -> None:
    client, fake, headers = api
    fake.sorties = [sortie("ok")]
    client.post(URL, json={"message": "Quels documents fournir ?"}, headers=headers)

    instructions = fake.appels[0][0]["content"]
    assert "ne la présente\n   jamais comme officielle" in instructions
    assert "questions de suivi" in instructions
    assert "ambiguë" in instructions


# ------------------------------------------------------------------ questions ambiguës
def test_question_ambigue_le_modele_demande_une_precision(api) -> None:
    client, fake, headers = api
    fake.sorties = [sortie("De quels frais parles-tu : IIT ou ISB ?", "INFO_FORMATION")]
    r = client.post(URL, json={"message": "C'est combien ?"}, headers=headers)

    assert r.status_code == 200
    assert r.json()["repli"] is False
    assert r.json()["reponse"].endswith("?")


# ------------------------------------------------------------------ le modèle ne peut pas répondre
@pytest.mark.parametrize(
    "sortie_modele", ["", "texte sans JSON", sortie("")], ids=["vide", "non_json", "sans_reponse"]
)
def test_reponse_inexploitable_demande_une_reformulation(api, sortie_modele: str) -> None:
    client, fake, headers = api
    fake.sorties = [sortie_modele]
    r = client.post(URL, json={"message": "9adeh?"}, headers=headers)

    assert r.status_code == 200
    assert r.json()["repli"] is True
    assert r.json()["reponse"] == MESSAGE_REPLI
    assert memoire(client, headers)[-1]["content"] == MESSAGE_REPLI


# ------------------------------------------------------------------ LLM indisponible
@pytest.mark.parametrize(
    ("erreur", "statut"),
    [
        (AppError("indisponible", code="llm_unavailable", status_code=503), 503),
        (AppError("trop long", code="llm_timeout", status_code=504), 504),
    ],
    ids=["indisponible", "delai_depasse"],
)
def test_llm_temporairement_indisponible(api, erreur: AppError, statut: int) -> None:
    client, fake, headers = api
    fake.sorties = [erreur, sortie("Me revoilà !")]
    r = client.post(URL, json={"message": "Bonjour"}, headers=headers)
    assert r.status_code == statut
    assert r.json()["error"]["code"] == erreur.code
    assert all(m["role"] == "user" for m in memoire(client, headers))  # aucune réponse inventée

    # Le service revient : la conversation continue normalement
    r = client.post(URL, json={"message": "Tu es là ?"}, headers=headers)
    assert r.status_code == 200
    assert r.json()["reponse"] == "Me revoilà !"


# ------------------------------------------------------------------ session
def test_sans_session_visiteur_refuse(api) -> None:
    client, fake, _ = api
    r = client.post(URL, json={"message": "Bonjour"})
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "visitor_token_missing"
    assert fake.appels == []


def test_session_terminee_refusee(api) -> None:
    client, fake, headers = api
    client.delete(f"{SESSIONS}/me", headers=headers)
    r = client.post(URL, json={"message": "Bonjour"}, headers=headers)
    assert r.status_code == 401
    assert fake.appels == []


def test_limite_de_messages_atteinte_sans_appeler_le_modele(api, monkeypatch) -> None:
    client, fake, headers = api
    monkeypatch.setattr(settings, "VISITOR_MAX_MESSAGES_PER_SESSION", 1)
    fake.sorties = [sortie("ok")]
    assert client.post(URL, json={"message": "Bonjour"}, headers=headers).status_code == 200

    r = client.post(URL, json={"message": "Encore une question"}, headers=headers)
    assert r.status_code == 429
    assert r.json()["error"]["code"] == "message_limit_reached"
    assert len(fake.appels) == 1
