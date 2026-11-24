"""SA-37 : conversation avec le LLM en s'appuyant sur la mémoire temporaire de la session.

À chaque question du visiteur :
1. lecture de la mémoire de la session (SA-26) : messages récents et fiche du visiteur ;
2. enregistrement de la question (compte dans la limite de messages de SA-25) ;
3. envoi au modèle : instructions + fiche + messages récents + nouvelle question ;
4. enregistrement de la réponse du modèle dans la mémoire.
"""

from redis import Redis

from app.core.config import settings
from app.models.enums import MessageRole
from app.schemas.visitor_memory import MemoryMessageIn
from app.services import llm, visitor_memory

ROLES_TRANSMIS = {MessageRole.user, MessageRole.assistant}


def repondre(redis: Redis, token: str, question: str, client: llm.LLMClient) -> llm.ReponseLLM:
    memoire = visitor_memory.get_memory(redis, token)  # 401 si la session a expiré
    historique = [
        {"role": m.role.value, "content": m.content}
        for m in memoire.messages
        if m.role in ROLES_TRANSMIS
    ][-settings.LLM_HISTORY_MAX_MESSAGES :]
    fiche = memoire.facts.model_dump(exclude_none=True, mode="json")

    # Enregistrée avant l'appel au modèle : les limites de la session (429) s'appliquent
    # avant de solliciter le LLM.
    visitor_memory.add_message(
        redis, token, MemoryMessageIn(role=MessageRole.user, content=question)
    )

    resultat = llm.generer(client, llm.construire_messages(question, historique, fiche))

    visitor_memory.add_message(
        redis, token, MemoryMessageIn(role=MessageRole.assistant, content=resultat.reponse)
    )
    return resultat
