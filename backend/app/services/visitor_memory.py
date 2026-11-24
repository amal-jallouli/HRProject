"""Mémoire temporaire des conversations visiteurs (SA-26).

Stockage dans Redis, rattaché à la session visiteur de SA-25 :
  visitor_memory:<hash du jeton>:messages -> liste des derniers messages (JSON), les plus
                                             anciens sont supprimés au-delà de la limite
  visitor_memory:<hash du jeton>:facts    -> fiche du visiteur (JSON) : informations utiles
                                             déjà obtenues (bac, moyenne, intérêts...)

Les deux clés expirent EN MÊME TEMPS que la session : la mémoire ne survit jamais
à la session. Rien n'est écrit dans PostgreSQL.
"""

import json
from datetime import UTC, datetime

from redis import Redis

from app.core.config import settings
from app.models.enums import MessageRole
from app.schemas.visitor_memory import (
    MemoryMessageIn,
    MemoryMessageOut,
    VisitorFacts,
    VisitorMemoryOut,
)
from app.services import visitor_session as session_service

MEMORY_PREFIX = "visitor_memory:"


def _messages_key(token: str) -> str:
    return f"{MEMORY_PREFIX}{session_service.hash_token(token)}:messages"


def _facts_key(token: str) -> str:
    return f"{MEMORY_PREFIX}{session_service.hash_token(token)}:facts"


# ------------------------------------------------------------------ messages
def add_message(redis: Redis, token: str, message: MemoryMessageIn) -> MemoryMessageOut:
    """Enregistre un message dans la mémoire de la session.

    Les messages du visiteur (role=user) comptent dans la limite de messages de SA-25.
    """
    if message.role == MessageRole.user:
        session = session_service.register_message(redis, token)  # 401 / 429
    else:
        session = session_service.get_session(redis, token)  # 401 si expirée

    stored = MemoryMessageOut(
        role=message.role, content=message.content, created_at=datetime.now(UTC)
    )
    key = _messages_key(token)
    redis.rpush(key, stored.model_dump_json())
    # Ne garde que les N derniers messages : les plus anciens sont supprimés
    redis.ltrim(key, -settings.VISITOR_MEMORY_MAX_MESSAGES, -1)
    # La mémoire expire au même moment que la session
    redis.expire(key, session.expires_in_seconds)
    return stored


# ------------------------------------------------------------------ fiche du visiteur
def update_facts(redis: Redis, token: str, new_facts: VisitorFacts) -> VisitorFacts:
    """Complète la fiche du visiteur : les champs envoyés remplacent les anciens,
    les autres sont conservés."""
    session = session_service.get_session(redis, token)  # 401 si expirée
    current = _read_facts(redis, token)
    merged = current.model_copy(update=new_facts.model_dump(exclude_unset=True))
    redis.set(
        _facts_key(token),
        merged.model_dump_json(exclude_none=True),
        ex=session.expires_in_seconds,  # même expiration que la session
    )
    return merged


def _read_facts(redis: Redis, token: str) -> VisitorFacts:
    raw = redis.get(_facts_key(token))
    return VisitorFacts.model_validate_json(raw) if raw else VisitorFacts()


# ------------------------------------------------------------------ lecture
def get_memory(redis: Redis, token: str) -> VisitorMemoryOut:
    """Retourne la mémoire complète : c'est le contexte que lira l'agent IA."""
    session = session_service.get_session(redis, token)  # 401 si expirée
    raw_messages = redis.lrange(_messages_key(token), 0, -1)
    return VisitorMemoryOut(
        messages=[MemoryMessageOut.model_validate(json.loads(m)) for m in raw_messages],
        facts=_read_facts(redis, token),
        max_messages=settings.VISITOR_MEMORY_MAX_MESSAGES,
        expires_in_seconds=session.expires_in_seconds,
    )


# ------------------------------------------------------------------ effacement
def clear_memory(redis: Redis, token: str) -> None:
    """Efface immédiatement toute la mémoire de la session."""
    redis.delete(_messages_key(token), _facts_key(token))