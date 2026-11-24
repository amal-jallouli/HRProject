"""Sessions des visiteurs sans compte (SA-25) et leur mémoire temporaire (SA-26).

Le visiteur s'identifie avec l'en-tête `X-Visitor-Token` (jeton reçu à la création).
Ce mécanisme est SÉPARÉ de l'authentification des responsables (`X-User-Email`, deps.py).
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.security import APIKeyHeader

from app.core.exceptions import AppError
from app.core.redis_client import RedisClient
from app.schemas.visitor_memory import (
    MemoryMessageIn,
    MemoryMessageOut,
    VisitorFacts,
    VisitorMemoryOut,
)
from app.schemas.visitor_session import VisitorSessionCreated, VisitorSessionOut
from app.services import visitor_memory as memory
from app.services import visitor_session as service

router = APIRouter(prefix="/visitor-sessions", tags=["sessions visiteurs"])

_visitor_token_header = APIKeyHeader(
    name="X-Visitor-Token",
    scheme_name="VisitorToken",
    auto_error=False,
    description="Jeton de session visiteur renvoyé par POST /visitor-sessions",
)


def get_visitor_token(
    redis: RedisClient,
    token: Annotated[str | None, Depends(_visitor_token_header)],
) -> str:
    """Exige un jeton visiteur et applique la limite de requêtes par minute."""
    if not token:
        raise AppError(
            "En-tête X-Visitor-Token manquant.",
            code="visitor_token_missing",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )
    service.get_session(redis, token)  # 401 si la session est inconnue ou expirée
    service.check_rate_limit(redis, token)  # 429 si trop de requêtes
    return token


VisitorToken = Annotated[str, Depends(get_visitor_token)]


# ------------------------------------------------------------------ sessions (SA-25)
@router.post(
    "",
    response_model=VisitorSessionCreated,
    status_code=status.HTTP_201_CREATED,
    summary="Créer une session visiteur",
)
def create_visitor_session(request: Request, redis: RedisClient) -> VisitorSessionCreated:
    client_ip = request.client.host if request.client else "unknown"
    token, session = service.create_session(redis, client_ip)
    return VisitorSessionCreated(**session.model_dump(), token=token)


@router.get("/me", response_model=VisitorSessionOut, summary="Consulter sa session")
def read_visitor_session(token: VisitorToken, redis: RedisClient) -> VisitorSessionOut:
    return service.get_session(redis, token)


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT, summary="Terminer sa session")
def delete_visitor_session(token: VisitorToken, redis: RedisClient) -> Response:
    memory.clear_memory(redis, token)  # SA-26 : la mémoire disparaît avec la session
    service.end_session(redis, token)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ------------------------------------------------------------------ mémoire (SA-26)
@router.post(
    "/me/messages",
    response_model=MemoryMessageOut,
    status_code=status.HTTP_201_CREATED,
    summary="Enregistrer un message dans la mémoire",
)
def add_memory_message(
    message: MemoryMessageIn, token: VisitorToken, redis: RedisClient
) -> MemoryMessageOut:
    return memory.add_message(redis, token, message)


@router.get("/me/memory", response_model=VisitorMemoryOut, summary="Lire la mémoire")
def read_memory(token: VisitorToken, redis: RedisClient) -> VisitorMemoryOut:
    return memory.get_memory(redis, token)


@router.patch(
    "/me/memory/facts",
    response_model=VisitorFacts,
    response_model_exclude_none=True,
    summary="Compléter la fiche du visiteur",
)
def update_memory_facts(
    facts: VisitorFacts, token: VisitorToken, redis: RedisClient
) -> VisitorFacts:
    return memory.update_facts(redis, token, facts)