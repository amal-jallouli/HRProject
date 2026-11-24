"""SA-36 : API de dialogue avec le LLM (le modèle est simulé, Ollama n'est pas nécessaire)."""

import json
from collections.abc import Iterator

import pytest
from app.api.v1.llm import get_llm_client
from app.core.exceptions import AppError
from app.main import app
from app.services import llm as service
from app.services.llm_prompt import MESSAGE_REPLI
from fastapi.testclient import TestClient


class FakeLLMClient(service.LLMClient):
    """Renvoie une réponse préparée à l'avance ou lève l'erreur demandée."""

    def __init__(self, sortie: str | Exception = "", statut: dict | None = None):
        super().__init__()
        self.sortie = sortie
        self._statut = statut or {}
        self.messages_recus: list[dict[str, str]] = []

    def chat(self, messages: list[dict[str, str]]) -> str:
        self.messages_recus = messages
        if isinstance(self.sortie, Exception):
            raise self.sortie
        return self.sortie

    def statut(self) -> dict:
        return self._statut


def sortie_json(**champs) -> str:
    base = {"langue": "fr", "intention": "ORIENTATION", "profil": {}, "reponse": "Bonjour !"}
    return json.dumps(base | champs, ensure_ascii=False)


@pytest.fixture
def api() -> Iterator:
    """Client de test avec un LLM simulé (pas de base de données nécessaire)."""
    fake = FakeLLMClient()
    app.dependency_overrides[get_llm_client] = lambda: fake
    yield TestClient(app), fake
    app.dependency_overrides.clear()


def test_question_renvoie_une_reponse_structuree(api) -> None:
    client, fake = api
    fake.sortie = sortie_json(
        intention="ORIENTATION",
        profil={"section_bac": "mathématiques", "moyenne": 14},
        reponse="Je te propose la licence ou la prépa. Tu préfères la théorie ou la pratique ?",
    )
    r = client.post("/api/v1/llm/chat", json={"message": "J'ai 14 au bac maths, je fais quoi ?"})
    assert r.status_code == 200
    body = r.json()
    assert body["intention"] == "ORIENTATION"
    assert body["langue"] == "fr"
    assert body["profil"] == {"section_bac": "mathématiques", "moyenne": 14}
    assert body["repli"] is False
    assert body["reponse"].startswith("Je te propose")


def test_le_prompt_systeme_et_la_question_sont_envoyes(api) -> None:
    client, fake = api
    fake.sortie = sortie_json()
    client.post("/api/v1/llm/chat", json={"message": "  Bonjour  "})
    assert fake.messages_recus[0]["role"] == "system"
    assert "N'invente jamais" in fake.messages_recus[0]["content"]
    assert fake.messages_recus[1] == {"role": "user", "content": "Bonjour"}


@pytest.mark.parametrize("message", ["", "x" * 2001], ids=["vide", "trop_long"])
def test_message_vide_ou_trop_long_refuse(api, message: str) -> None:
    client, _ = api
    r = client.post("/api/v1/llm/chat", json={"message": message})
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "validation_error"


def test_serveur_indisponible_renvoie_503(api) -> None:
    client, fake = api
    fake.sortie = AppError("indisponible", code="llm_unavailable", status_code=503)
    r = client.post("/api/v1/llm/chat", json={"message": "Bonjour"})
    assert r.status_code == 503
    assert r.json()["error"]["code"] == "llm_unavailable"


def test_delai_depasse_renvoie_504(api) -> None:
    client, fake = api
    fake.sortie = AppError("trop long", code="llm_timeout", status_code=504)
    r = client.post("/api/v1/llm/chat", json={"message": "Bonjour"})
    assert r.status_code == 504
    assert r.json()["error"]["code"] == "llm_timeout"


@pytest.mark.parametrize(
    "sortie",
    [
        "texte sans JSON",
        "",
        sortie_json(reponse=""),
        sortie_json(intention="INTENTION_INCONNUE"),
    ],
)
def test_sortie_inexploitable_declenche_le_repli(api, sortie: str) -> None:
    client, fake = api
    fake.sortie = sortie
    r = client.post("/api/v1/llm/chat", json={"message": "9adeh?"})
    assert r.status_code == 200
    assert r.json()["repli"] is True
    assert r.json()["reponse"] == MESSAGE_REPLI


def test_statut_du_llm(api) -> None:
    client, fake = api
    fake._statut = {"serveur": "up", "modele": "gemma4:e2b-it-qat", "modele_installe": True}
    r = client.get("/api/v1/llm/status")
    assert r.status_code == 200
    assert r.json()["modele_installe"] is True
