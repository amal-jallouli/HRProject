"""SA-38 : test du dialogue réel avec le LLM à travers l'API Backend.

Prérequis : Redis lancé (docker compose up -d), Ollama lancé avec le modèle configuré,
API lancée (cd backend && uvicorn app.main:app --reload).

    python scripts/test_dialogue_llm.py

Joue une conversation en français (questions successives, suivi de contexte, question
ambiguë, information administrative) et enregistre le résultat dans
scripts/resultats_dialogue_llm.md.
"""

import re
import sys
import time
from pathlib import Path

import httpx

API = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
RAPPORT = Path(__file__).with_name("resultats_dialogue_llm.md")

# (question, ce qui est vérifié)
SCENARIO = [
    ("Bonjour, je suis en terminale et je cherche une formation.", "accueil"),
    ("J'ai un bac maths avec 14 de moyenne et j'aime la programmation.", "profil"),
    ("Tu me conseilles quoi ?", "contexte"),
    ("Et à l'ISB, c'est possible ?", "suivi"),
    ("C'est combien ?", "ambigu"),
    ("Quels sont les frais exacts de la licence à l'IIT ?", "administratif"),
    ("Rappelle-moi ma moyenne, s'il te plaît.", "memoire"),
]


def verifier(cas: str, reponse: str) -> tuple[bool, str]:
    r = reponse.lower()
    if cas == "ambigu":
        return "?" in reponse, "demande une précision"
    if cas == "administratif":
        prudent = any(m in r for m in ["vérif", "confirm", "admission", "officiel"])
        montant = re.search(r"\d+\s*(dt|dinars?|tnd)", r)
        return prudent and not montant, "ne présente pas de montant comme officiel"
    if cas == "memoire":
        return "14" in reponse, "rappelle la moyenne donnée au 2e message"
    if cas == "contexte":
        return any(m in r for m in ["math", "programm", "informatique"]), "utilise le profil donné"
    return bool(reponse.strip()), "réponse non vide"


def main() -> None:
    lignes = ["# SA-38 — Test du dialogue avec le LLM\n"]
    with httpx.Client(base_url=API, timeout=300) as client:
        statut = client.get("/api/v1/llm/status").json()
        print("Statut LLM :", statut)
        if statut.get("serveur") != "up" or not statut.get("modele_installe"):
            sys.exit("Ollama n'est pas prêt : lancez Ollama et installez le modèle configuré.")
        token = client.post("/api/v1/visitor-sessions").json()["token"]
        headers = {"X-Visitor-Token": token}

        lignes.append(f"Modèle : `{statut['modele']}`\n")
        lignes.append(
            "| # | Candidat | Réponse du LLM | Intention | Repli | Latence | Vérification |"
        )
        lignes.append("|---|---|---|---|---|---|---|")
        reussis = 0
        for i, (question, cas) in enumerate(SCENARIO, 1):
            debut = time.perf_counter()
            r = client.post("/api/v1/llm/conversation", json={"message": question}, headers=headers)
            duree = time.perf_counter() - debut
            if r.status_code != 200:
                print(f"[{i}] ERREUR {r.status_code} : {r.text}")
                lignes.append(f"| {i} | {question} | erreur {r.status_code} | | | | ❌ |")
                continue
            body = r.json()
            ok, critere = verifier(cas, body["reponse"])
            reussis += ok
            print(f"\n[{i}] Candidat : {question}\n    LLM : {body['reponse']}")
            print(
                f"    intention={body['intention']}  repli={body['repli']}  {duree:.1f}s  "
                f"{'OK' if ok else 'KO'} ({critere})"
            )
            reponse = body["reponse"].replace("|", "/").replace("\n", " ")
            lignes.append(
                f"| {i} | {question} | {reponse} | {body['intention']} | {body['repli']} "
                f"| {duree:.1f} s | {'✅' if ok else '❌'} {critere} |"
            )
        nb = len(
            client.get("/api/v1/visitor-sessions/me/memory", headers=headers).json()["messages"]
        )
        client.delete("/api/v1/visitor-sessions/me", headers=headers)

    lignes.append(
        f"\n**Vérifications réussies : {reussis}/{len(SCENARIO)}** — "
        f"messages conservés en mémoire : {nb}\n"
    )
    RAPPORT.write_text("\n".join(lignes), encoding="utf-8")
    print(f"\n{reussis}/{len(SCENARIO)} vérifications réussies. Rapport : {RAPPORT}")


if __name__ == "__main__":
    main()
