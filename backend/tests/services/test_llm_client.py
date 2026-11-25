"""SA-36 : client HTTP vers Ollama (réseau simulé avec httpx.MockTransport)."""

import json

import httpx
import pytest
from app.core.config import Settings
from app.core.exceptions import AppError
from app.services.llm import LLMClient, lire_json
from pydantic import SecretStr


def client_avec(handler, **config) -> LLMClient:
    reglages = Settings(LLM_MODEL="gemma4:e2b-it-qat", **config)
    return LLMClient(reglages, transport=httpx.MockTransport(handler))


def reponse_ollama(contenu: str) -> httpx.Response:
    return httpx.Response(200, json={"message": {"role": "assistant", "content": contenu}})


def test_envoie_les_parametres_configures() -> None:
    recu = {}

    def handler(request: httpx.Request) -> httpx.Response:
        recu.update(json.loads(request.content))
        return reponse_ollama('{"reponse": "ok"}')

    texte = client_avec(handler, LLM_TEMPERATURE=0.1, LLM_MAX_TOKENS=200).chat(
        [{"role": "user", "content": "Bonjour"}]
    )
    assert texte == '{"reponse": "ok"}'
    assert recu["model"] == "gemma4:e2b-it-qat"
    assert recu["options"]["temperature"] == 0.1
    assert recu["options"]["num_predict"] == 200
    assert recu["stream"] is False


def test_cle_d_acces_envoyee_dans_l_en_tete_uniquement() -> None:
    entetes = {}

    def handler(request: httpx.Request) -> httpx.Response:
        entetes.update(request.headers)
        return reponse_ollama("{}")

    client = client_avec(handler, LLM_API_KEY=SecretStr("cle-secrete"))
    client.chat([{"role": "user", "content": "Bonjour"}])
    assert entetes["authorization"] == "Bearer cle-secrete"
    assert "cle-secrete" not in repr(client.config)  # jamais affichée


def test_sans_cle_aucun_en_tete_d_autorisation() -> None:
    entetes = {}

    def handler(request: httpx.Request) -> httpx.Response:
        entetes.update(request.headers)
        return reponse_ollama("{}")

    client_avec(handler).chat([{"role": "user", "content": "Bonjour"}])
    assert "authorization" not in entetes


@pytest.mark.parametrize(
    ("exception", "code", "status"),
    [
        (httpx.ConnectError("refus"), "llm_unavailable", 503),
        (httpx.ReadTimeout("lent"), "llm_timeout", 504),
        (httpx.ConnectTimeout("lent"), "llm_timeout", 504),
    ],
)
def test_erreurs_reseau_converties(exception, code: str, status: int) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise exception

    with pytest.raises(AppError) as erreur:
        client_avec(handler).chat([{"role": "user", "content": "Bonjour"}])
    assert erreur.value.code == code
    assert erreur.value.status_code == status


def test_modele_absent_renvoie_une_erreur_claire() -> None:
    with pytest.raises(AppError) as erreur:
        client_avec(lambda r: httpx.Response(404, json={"error": "model not found"})).chat([])
    assert erreur.value.code == "llm_model_not_found"


def test_erreur_serveur_renvoie_indisponible() -> None:
    with pytest.raises(AppError) as erreur:
        client_avec(lambda r: httpx.Response(500)).chat([])
    assert erreur.value.code == "llm_unavailable"


def test_modele_sans_mode_thinking_relance_sans_ce_parametre() -> None:
    payloads = []

    def handler(request: httpx.Request) -> httpx.Response:
        payloads.append(json.loads(request.content))
        if "think" in payloads[-1]:
            return httpx.Response(400, json={"error": "model does not support think"})
        return reponse_ollama("{}")

    client_avec(handler).chat([])
    assert "think" in payloads[0] and "think" not in payloads[1]


def test_statut_serveur() -> None:
    up = client_avec(
        lambda r: httpx.Response(200, json={"models": [{"name": "gemma4:e2b-it-qat"}]})
    )
    assert up.statut() == {"serveur": "up", "modele": "gemma4:e2b-it-qat", "modele_installe": True}

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refus")

    assert client_avec(handler).statut()["serveur"] == "down"


@pytest.mark.parametrize(
    ("texte", "attendu"),
    [
        ('{"a": 1}', {"a": 1}),
        ('```json\n{"a": 1}\n```', {"a": 1}),
        ('Voici : {"a": 1} fin', {"a": 1}),
        ("pas de json", None),
        ("[1, 2]", None),
    ],
)
def test_lire_json(texte: str, attendu) -> None:
    assert lire_json(texte) == attendu
