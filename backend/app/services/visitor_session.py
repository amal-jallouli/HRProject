"""Logique des sessions visiteurs (SA-25) : création, lecture, expiration et limites.

Stockage dans Redis (aucune table PostgreSQL) :
  visitor_session:<hash du jeton>       -> hash {session_id, created_at, expires_at, messages_used}
                                           supprimé automatiquement par Redis à l'expiration (TTL)
  visitor_rate:<hash du jeton>:<minute> -> compteur de requêtes de la minute en cours (TTL 60 s)
  visitor_ip:<adresse IP>               -> compteur de sessions créées par cette IP (TTL 1 h)

Le jeton n'est JAMAIS stocké en clair : seul son hash SHA-256 sert de clé
(même principe que la colonne conversations.guest_token_hash).
"""

import hashlib
import secrets
import time
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import status
from redis import Redis

from app.core.config import settings
from app.core.exceptions import AppError
from app.schemas.visitor_session import VisitorSessionLimits, VisitorSessionOut

SESSION_PREFIX = "visitor_session:"
RATE_PREFIX = "visitor_rate:"
IP_PREFIX = "visitor_ip:"


def hash_token(token: str) -> str:
    """Hash SHA-256 du jeton : c'est la seule forme stockée côté serveur."""
    return hashlib.sha256(token.encode()).hexdigest()


def _session_key(token_hash: str) -> str:
    return f"{SESSION_PREFIX}{token_hash}"


# ------------------------------------------------------------------ création
def create_session(redis: Redis, client_ip: str) -> tuple[str, VisitorSessionOut]:
    """Crée une session visiteur et renvoie (jeton en clair, état de la session)."""
    _check_ip_limit(redis, client_ip)

    token = secrets.token_urlsafe(32)  # jeton aléatoire, impossible à deviner
    ttl_seconds = settings.VISITOR_SESSION_TTL_MINUTES * 60
    created_at = datetime.now(UTC)
    expires_at = created_at + timedelta(seconds=ttl_seconds)

    key = _session_key(hash_token(token))
    redis.hset(
        key,
        mapping={
            "session_id": str(uuid.uuid4()),
            "created_at": created_at.isoformat(),
            "expires_at": expires_at.isoformat(),
            "messages_used": 0,
        },
    )
    redis.expire(key, ttl_seconds)  # expiration automatique gérée par Redis

    return token, get_session(redis, token)


def _check_ip_limit(redis: Redis, client_ip: str) -> None:
    """Refuse la création si cette IP a déjà créé trop de sessions dans l'heure."""
    key = f"{IP_PREFIX}{client_ip}"
    count = redis.incr(key)
    if count == 1:
        redis.expire(key, 3600)  # le compteur repart à zéro après 1 heure
    if count > settings.VISITOR_MAX_SESSIONS_PER_IP_PER_HOUR:
        raise AppError(
            "Trop de sessions créées depuis cette adresse. Réessayez plus tard.",
            code="too_many_sessions",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        )


# ------------------------------------------------------------------ lecture / validité
def get_session(redis: Redis, token: str) -> VisitorSessionOut:
    """Retourne l'état de la session ; 401 si le jeton est inconnu ou la session expirée."""
    key = _session_key(hash_token(token))
    data = redis.hgetall(key)
    remaining = redis.ttl(key)  # secondes restantes (-2 si la clé n'existe plus)
    if not data or remaining <= 0:
        raise AppError(
            "Session visiteur invalide ou expirée.",
            code="visitor_session_expired",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    messages_used = int(data["messages_used"])
    max_messages = settings.VISITOR_MAX_MESSAGES_PER_SESSION
    return VisitorSessionOut(
        session_id=data["session_id"],
        created_at=data["created_at"],
        expires_at=data["expires_at"],
        expires_in_seconds=remaining,
        is_valid=True,
        messages_used=messages_used,
        messages_remaining=max(max_messages - messages_used, 0),
        limits=VisitorSessionLimits(
            requests_per_minute=settings.VISITOR_RATE_LIMIT_PER_MINUTE,
            max_messages=max_messages,
        ),
    )


# ------------------------------------------------------------------ limites d'utilisation
def check_rate_limit(redis: Redis, token: str) -> None:
    """Compte les requêtes de la minute en cours ; 429 au-delà de la limite."""
    minute = int(time.time() // 60)
    key = f"{RATE_PREFIX}{hash_token(token)}:{minute}"
    count = redis.incr(key)
    if count == 1:
        redis.expire(key, 60)
    if count > settings.VISITOR_RATE_LIMIT_PER_MINUTE:
        raise AppError(
            "Trop de requêtes. Patientez une minute.",
            code="rate_limited",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        )


def register_message(redis: Redis, token: str) -> VisitorSessionOut:
    """Compte un message envoyé par le visiteur ; 429 si la limite de la session est atteinte.

    Sera appelée par l'endpoint de conversation (SA-24 / SA-26).
    """
    session = get_session(redis, token)  # 401 si expirée
    if session.messages_remaining <= 0:
        raise AppError(
            "Nombre maximal de messages atteint pour cette session.",
            code="message_limit_reached",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        )
    redis.hincrby(_session_key(hash_token(token)), "messages_used", 1)
    return get_session(redis, token)


# ------------------------------------------------------------------ fin de session
def end_session(redis: Redis, token: str) -> None:
    """Termine la session immédiatement (le visiteur quitte le chat)."""
    get_session(redis, token)  # 401 si déjà expirée
    redis.delete(_session_key(hash_token(token)))