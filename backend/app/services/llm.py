"""SA-36 : service de communication avec le LLM sélectionné (Ollama).

- Les paramètres (URL, modèle, délai, clé d'accès) viennent de `app.core.config.settings`.
- Les erreurs de connexion et les dépassements de délai sont convertis en `AppError`,
  donc renvoyés au format d'erreur commun de l'API.
- `generer()` reçoit une liste de messages : SA-37 pourra y ajouter l'historique de la session.
"""

import json
import re
import time
from dataclasses import dataclass, field
from typing import Any

import httpx
from fastapi import status

from app.core.config import Settings, settings
from app.core.exceptions import AppError
from app.services.llm_prompt import INTENTIONS, MESSAGE_REPLI, OUTPUT_SCHEMA, SYSTEM_PROMPT


@dataclass
class ReponseLLM:
    reponse: str
    intention: str | None
    langue: str | None
    profil: dict[str, Any] = field(default_factory=dict)
    repli: bool = False
    modele: str = ""
    latence_s: float = 0.0


class LLMClient:
    """Client HTTP vers l'API d'Ollama."""

    def __init__(self, config: Settings = settings, transport: httpx.BaseTransport | None = None):
        self.config = config
        self._transport = transport  # remplaçable dans les tests

    def _headers(self) -> dict[str, str]:
        if self.config.LLM_API_KEY is None:
            return {}
        return {"Authorization": f"Bearer {self.config.LLM_API_KEY.get_secret_value()}"}

    def _client(self, timeout: float) -> httpx.Client:
        return httpx.Client(
            base_url=self.config.LLM_BASE_URL,
            headers=self._headers(),
            timeout=timeout,
            transport=self._transport,
        )

    def chat(self, messages: list[dict[str, str]]) -> str:
        """Envoie les messages au modèle et renvoie le texte brut de sa réponse."""
        payload: dict[str, Any] = {
            "model": self.config.LLM_MODEL,
            "messages": messages,
            "stream": False,
            "format": OUTPUT_SCHEMA,
            "think": False,
            "options": {
                "temperature": self.config.LLM_TEMPERATURE,
                "num_predict": self.config.LLM_MAX_TOKENS,
                "num_ctx": self.config.LLM_CONTEXT_SIZE,
            },
        }
        try:
            with self._client(self.config.LLM_TIMEOUT_SECONDS) as client:
                response = client.post("/api/chat", json=payload)
                if response.status_code == status.HTTP_400_BAD_REQUEST and "think" in response.text:
                    payload.pop("think")  # modèle sans mode « thinking »
                    response = client.post("/api/chat", json=payload)
                if response.status_code == status.HTTP_404_NOT_FOUND:
                    raise AppError(
                        f"Le modèle « {self.config.LLM_MODEL} » n'est pas installé sur le serveur.",
                        code="llm_model_not_found",
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    )
                response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise AppError(
                "Le modèle a mis trop de temps à répondre. Veuillez réessayer.",
                code="llm_timeout",
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            ) from exc
        except httpx.HTTPError as exc:
            raise AppError(
                "Le service de génération est momentanément indisponible.",
                code="llm_unavailable",
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            ) from exc
        return response.json().get("message", {}).get("content", "")

    def statut(self) -> dict[str, Any]:
        """Indique si le serveur répond et si le modèle configuré est installé."""
        try:
            with self._client(timeout=5) as client:
                modeles = [m["name"] for m in client.get("/api/tags").json().get("models", [])]
        except (httpx.HTTPError, ValueError):
            return {"serveur": "down", "modele": self.config.LLM_MODEL, "modele_installe": False}
        return {
            "serveur": "up",
            "modele": self.config.LLM_MODEL,
            "modele_installe": self.config.LLM_MODEL in modeles,
        }


def lire_json(texte: str) -> dict[str, Any] | None:
    """Extrait l'objet JSON produit par le modèle (tolère ```json ... ``` autour)."""
    texte = re.sub(r"^```(?:json)?|```$", "", texte.strip(), flags=re.M).strip()
    trouve = re.search(r"\{.*\}", texte, flags=re.S)
    if not trouve:
        return None
    try:
        objet = json.loads(trouve.group(0))
    except json.JSONDecodeError:
        return None
    return objet if isinstance(objet, dict) else None


def construire_messages(
    question: str,
    historique: list[dict[str, str]] | None = None,
    fiche: dict[str, Any] | None = None,
) -> list[dict[str, str]]:
    """Prompt système + informations connues sur le candidat + messages récents + question."""
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if fiche:
        connu = json.dumps(fiche, ensure_ascii=False, default=str)
        messages.append(
            {
                "role": "system",
                "content": f"Informations déjà connues sur le candidat (ne pas les redemander) : "
                f"{connu}",
            }
        )
    messages += historique or []
    messages.append({"role": "user", "content": question})
    return messages


def generer(client: LLMClient, messages: list[dict[str, str]]) -> ReponseLLM:
    """Interroge le modèle ; si sa sortie est inexploitable, applique la solution de repli."""
    debut = time.perf_counter()
    sortie = lire_json(client.chat(messages)) or {}
    texte = str(sortie.get("reponse") or "").strip()
    intention = sortie.get("intention") if sortie.get("intention") in INTENTIONS else None
    profil = sortie.get("profil") if isinstance(sortie.get("profil"), dict) else {}
    repli = not texte or intention is None
    return ReponseLLM(
        reponse=MESSAGE_REPLI if repli else texte,
        intention=intention,
        langue=sortie.get("langue"),
        profil={} if repli else profil,
        repli=repli,
        modele=client.config.LLM_MODEL,
        latence_s=round(time.perf_counter() - debut, 2),
    )
