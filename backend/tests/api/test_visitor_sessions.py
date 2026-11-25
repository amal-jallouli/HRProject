"""Tests des sessions visiteurs (SA-25) et de leur mémoire temporaire (SA-26).

Ces tests utilisent la base Redis n°15 (et non la n°0 de l'application) : elle est vidée
avant et après chaque test, donc les vraies sessions ne sont jamais touchées.
Si Redis n'est pas joignable, les tests sont ignorés (comme ceux qui ont besoin de PostgreSQL).
"""

import time
from collections.abc import Iterator

import pytest
from app.core.config import settings
from app.core.redis_client import get_redis
from app.main import app
from app.services.visitor_session import hash_token
from fastapi.testclient import TestClient
from redis import Redis

BASE = "/api/v1/visitor-sessions"


# ------------------------------------------------------------------ fixtures
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
def visitor_client(redis_test: Redis) -> Iterator[TestClient]:
    app.dependency_overrides[get_redis] = lambda: redis_test
    yield TestClient(app)
    app.dependency_overrides.pop(get_redis, None)


def _new_session(client: TestClient) -> tuple[str, dict[str, str]]:
    response = client.post(BASE)
    assert response.status_code == 201
    token = response.json()["token"]
    return token, {"X-Visitor-Token": token}


# ------------------------------------------------------------------ SA-25 : sessions
def test_creation_session(visitor_client: TestClient) -> None:
    response = visitor_client.post(BASE)

    assert response.status_code == 201
    body = response.json()
    assert body["token"]
    assert body["session_id"]
    assert body["is_valid"] is True
    assert body["messages_used"] == 0
    assert body["expires_in_seconds"] == settings.VISITOR_SESSION_TTL_MINUTES * 60
    assert body["expires_at"] > body["created_at"]


def test_jeton_stocke_sous_forme_de_hash(visitor_client: TestClient, redis_test: Redis) -> None:
    token, _ = _new_session(visitor_client)

    assert redis_test.exists(f"visitor_session:{hash_token(token)}")
    assert not any(token in key for key in redis_test.keys("*"))


def test_recuperation_session(visitor_client: TestClient) -> None:
    token, headers = _new_session(visitor_client)

    response = visitor_client.get(f"{BASE}/me", headers=headers)

    assert response.status_code == 200
    assert "token" not in response.json()  # le secret n'est jamais renvoyé une 2e fois


def test_jeton_absent(visitor_client: TestClient) -> None:
    response = visitor_client.get(f"{BASE}/me")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "visitor_token_missing"


def test_jeton_invalide(visitor_client: TestClient) -> None:
    response = visitor_client.get(f"{BASE}/me", headers={"X-Visitor-Token": "faux"})

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "visitor_session_expired"


def test_expiration_automatique(visitor_client: TestClient, redis_test: Redis) -> None:
    token, headers = _new_session(visitor_client)
    redis_test.expire(f"visitor_session:{hash_token(token)}", 1)  # simule la fin du TTL
    time.sleep(1.5)

    response = visitor_client.get(f"{BASE}/me", headers=headers)

    assert response.status_code == 401


def test_limite_requetes_par_minute(
    visitor_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "VISITOR_RATE_LIMIT_PER_MINUTE", 2)
    _, headers = _new_session(visitor_client)

    codes = [visitor_client.get(f"{BASE}/me", headers=headers).status_code for _ in range(3)]

    assert codes == [200, 200, 429]


def test_limite_sessions_par_ip(
    visitor_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "VISITOR_MAX_SESSIONS_PER_IP_PER_HOUR", 2)

    codes = [visitor_client.post(BASE).status_code for _ in range(3)]

    assert codes == [201, 201, 429]


def test_fin_de_session(visitor_client: TestClient) -> None:
    _, headers = _new_session(visitor_client)

    assert visitor_client.delete(f"{BASE}/me", headers=headers).status_code == 204
    assert visitor_client.get(f"{BASE}/me", headers=headers).status_code == 401


# ------------------------------------------------------------------ SA-26 : mémoire
def test_enregistrement_et_lecture_des_messages(visitor_client: TestClient) -> None:
    _, headers = _new_session(visitor_client)
    visitor_client.post(
        f"{BASE}/me/messages", json={"content": "J'ai un bac info"}, headers=headers
    )
    visitor_client.post(
        f"{BASE}/me/messages",
        json={"role": "assistant", "content": "Quels domaines ?"},
        headers=headers,
    )

    memory = visitor_client.get(f"{BASE}/me/memory", headers=headers).json()

    assert [m["role"] for m in memory["messages"]] == ["user", "assistant"]
    assert memory["messages"][0]["content"] == "J'ai un bac info"


def test_seuls_les_messages_du_visiteur_sont_comptes(visitor_client: TestClient) -> None:
    _, headers = _new_session(visitor_client)
    visitor_client.post(f"{BASE}/me/messages", json={"content": "Bonjour"}, headers=headers)
    visitor_client.post(
        f"{BASE}/me/messages", json={"role": "assistant", "content": "Salut"}, headers=headers
    )

    session = visitor_client.get(f"{BASE}/me", headers=headers).json()

    assert session["messages_used"] == 1


def test_limite_messages_par_session(
    visitor_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "VISITOR_MAX_MESSAGES_PER_SESSION", 1)
    _, headers = _new_session(visitor_client)

    first = visitor_client.post(f"{BASE}/me/messages", json={"content": "1"}, headers=headers)
    second = visitor_client.post(f"{BASE}/me/messages", json={"content": "2"}, headers=headers)

    assert first.status_code == 201
    assert second.status_code == 429
    assert second.json()["error"]["code"] == "message_limit_reached"


def test_memoire_garde_les_derniers_messages(
    visitor_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "VISITOR_MEMORY_MAX_MESSAGES", 3)
    _, headers = _new_session(visitor_client)
    for i in range(5):
        visitor_client.post(f"{BASE}/me/messages", json={"content": f"msg {i}"}, headers=headers)

    memory = visitor_client.get(f"{BASE}/me/memory", headers=headers).json()

    assert [m["content"] for m in memory["messages"]] == ["msg 2", "msg 3", "msg 4"]


def test_message_trop_long_refuse(
    visitor_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "VISITOR_MESSAGE_MAX_LENGTH", 10)
    _, headers = _new_session(visitor_client)

    response = visitor_client.post(
        f"{BASE}/me/messages", json={"content": "x" * 11}, headers=headers
    )

    assert response.status_code == 422


def test_fiche_completee_sans_perte(visitor_client: TestClient) -> None:
    _, headers = _new_session(visitor_client)
    url = f"{BASE}/me/memory/facts"
    visitor_client.patch(
        url, json={"bac_section": "informatique", "average_grade": 14}, headers=headers
    )

    facts = visitor_client.patch(url, json={"interests": ["IA"]}, headers=headers).json()

    assert facts == {"bac_section": "informatique", "average_grade": "14", "interests": ["IA"]}


def test_fiche_refuse_champ_inconnu(visitor_client: TestClient) -> None:
    _, headers = _new_session(visitor_client)

    response = visitor_client.patch(
        f"{BASE}/me/memory/facts", json={"mot_de_passe": "1234"}, headers=headers
    )

    assert response.status_code == 422


def test_memoire_expire_avec_la_session(visitor_client: TestClient, redis_test: Redis) -> None:
    token, headers = _new_session(visitor_client)
    visitor_client.post(f"{BASE}/me/messages", json={"content": "Bonjour"}, headers=headers)
    visitor_client.patch(f"{BASE}/me/memory/facts", json={"goals": "ingénieur"}, headers=headers)

    session_ttl = redis_test.ttl(f"visitor_session:{hash_token(token)}")
    messages_ttl = redis_test.ttl(f"visitor_memory:{hash_token(token)}:messages")
    facts_ttl = redis_test.ttl(f"visitor_memory:{hash_token(token)}:facts")

    assert 0 < messages_ttl <= session_ttl
    assert 0 < facts_ttl <= session_ttl


def test_fin_de_session_efface_la_memoire(visitor_client: TestClient, redis_test: Redis) -> None:
    token, headers = _new_session(visitor_client)
    visitor_client.post(f"{BASE}/me/messages", json={"content": "Bonjour"}, headers=headers)
    visitor_client.patch(f"{BASE}/me/memory/facts", json={"goals": "ingénieur"}, headers=headers)

    visitor_client.delete(f"{BASE}/me", headers=headers)

    assert redis_test.keys(f"visitor_memory:{hash_token(token)}:*") == []