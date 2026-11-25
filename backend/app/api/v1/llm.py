"""SA-36 / SA-37 : API de dialogue avec le LLM sélectionné."""

from dataclasses import asdict
from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.v1.visitor_sessions import VisitorToken
from app.core.redis_client import RedisClient
from app.schemas.llm import QuestionIn, ReponseOut, StatutLLMOut
from app.services import llm as service
from app.services import llm_conversation

router = APIRouter(prefix="/llm", tags=["llm"])


def get_llm_client() -> service.LLMClient:
    """Dépendance remplaçable dans les tests."""
    return service.LLMClient()


LLMClientDep = Annotated[service.LLMClient, Depends(get_llm_client)]


@router.post("/chat", response_model=ReponseOut, summary="Envoyer une question au LLM")
def chat(question: QuestionIn, client: LLMClientDep) -> ReponseOut:
    messages = service.construire_messages(question.message.strip())
    return ReponseOut(**asdict(service.generer(client, messages)))


@router.post(
    "/conversation",
    response_model=ReponseOut,
    summary="Poser une question dans la conversation du visiteur (avec mémoire)",
)
def conversation(
    question: QuestionIn, token: VisitorToken, redis: RedisClient, client: LLMClientDep
) -> ReponseOut:
    """Le modèle reçoit les messages récents de la session (en-tête X-Visitor-Token)."""
    resultat = llm_conversation.repondre(redis, token, question.message.strip(), client)
    return ReponseOut(**asdict(resultat))


@router.get("/status", response_model=StatutLLMOut, summary="État du serveur LLM et du modèle")
def statut(client: LLMClientDep) -> StatutLLMOut:
    return StatutLLMOut(**client.statut())
