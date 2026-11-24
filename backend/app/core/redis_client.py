"""Connexion Redis partagée (SA-25 : sessions visiteurs)."""

from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from redis import Redis

from app.core.config import settings


@lru_cache
def get_redis() -> Redis:
    """Retourne un client Redis unique, réutilisé par toutes les requêtes."""
    return Redis.from_url(
        settings.REDIS_URL,
        decode_responses=True,  # Redis renvoie du texte (str) au lieu d'octets (bytes)
        socket_connect_timeout=2,  # abandonne après 2 s si Redis ne répond pas
    )


# Raccourci à utiliser dans les routes : `redis: RedisClient`
RedisClient = Annotated[Redis, Depends(get_redis)]