"""
SA-33 — Benchmark des LLM open-source (Ollama) pour SmartCampus AI.

Usage :
    python run_benchmark.py                          # modèles par défaut
    python run_benchmark.py --models qwen3.5:4b llama3.2:3b
    python run_benchmark.py --questions data/questions_eval_complement_FR.json

Les résultats bruts sont écrits au fur et à mesure dans results/raw_<modele>.jsonl :
si le script est interrompu, relancez-le, il reprend là où il s'est arrêté.
Ensuite : ouvrir analyse_resultats.ipynb et exécuter toutes les cellules
"""
import argparse, json, os, re, sys, time
import requests

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
DEFAULT_MODELS = ["qwen3.5:4b", "gemma4:e2b-it-qat", "llama3.2:3b"]
LANGUES = ["fr", "tn_ar", "arabizi", "mixte"]
LANG_DESC = {
    "fr": "français",
    "tn_ar": "dialecte tunisien écrit en alphabet arabe",
    "arabizi": "dialecte tunisien écrit en lettres latines et chiffres (3, 7, 9, 5...)",
    "mixte": "mélange de français et de dialecte tunisien dans le même message",
}


def build_prompt(meta):
    """Construit le prompt système à partir des intentions et champs de profil du fichier de questions."""
    langs = "\n".join(f'    "{k}" = {v},' for k, v in LANG_DESC.items())
    intents = "\n".join(f'    "{k}" = {v}' for k, v in meta["intentions"].items())
    keys = ", ".join(meta["champs_profil"])
    return f"""Tu es SmartCampus AI, l'assistant d'orientation universitaire de l'IIT et de l'ISB (Sfax, Tunisie).
Tu aides les futurs étudiants à choisir entre les parcours Licence, Prépa et Ingénierie de l'IIT et les formations de l'ISB,
tu construis leur profil, tu les accompagnes jusqu'à la préinscription, au QCM et au rendez-vous d'entretien.
Les candidats écrivent (ou parlent, message transcrit) en français, en dialecte tunisien, en Arabizi, ou en mélangeant ces langues.

Analyse le message du candidat et réponds UNIQUEMENT avec un objet JSON contenant :
- "langue" : une valeur parmi
{langs}
- "intention" : une valeur parmi
{intents}
- "profil" : objet avec les informations sur le candidat présentes dans le message, parmi les clés
    {keys}.
    N'inclus que les clés présentes dans le message ; objet vide {{}} sinon.
- "reponse" : ta réponse au candidat.

Règles pour "reponse" :
1. Réponds dans la même langue et le même registre que le candidat (s'il écrit en Arabizi, réponds en Arabizi).
2. N'invente JAMAIS de chiffres, de durées, de frais, de dates ni de conditions d'admission. Sans information officielle, dis que tu vas la vérifier.
3. Tu ne prends jamais de décision officielle (admission, acceptation) : indique qu'un responsable académique s'en charge.
4. Propose plusieurs options quand tu orientes, sans imposer de choix.
5. Si la demande est hors sujet, décline poliment et ramène la conversation vers l'orientation.
6. Sois bref : 4 phrases maximum."""


def build_schema(meta):
    return {
        "type": "object",
        "properties": {
            "langue": {"type": "string", "enum": LANGUES},
            "intention": {"type": "string", "enum": list(meta["intentions"])},
            "profil": {"type": "object"},
            "reponse": {"type": "string"},
        },
        "required": ["langue", "intention", "profil", "reponse"],
    }


def parse_json(text):
    """Extrait l'objet JSON de la sortie du modèle (tolère ```json ... ``` et texte autour)."""
    if not text:
        return None
    t = re.sub(r"<think>.*?</think>", "", text, flags=re.S).strip()
    t = re.sub(r"^```(?:json)?|```$", "", t.strip(), flags=re.M).strip()
    try:
        return json.loads(t)
    except Exception:
        m = re.search(r"\{.*\}", t, flags=re.S)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                return None
    return None


def call_ollama(model, question, prompt, schema, use_schema=True, timeout=600):
    payload = {
        "model": model,
        "messages": [{"role": "system", "content": prompt},
                     {"role": "user", "content": question}],
        "stream": False,
        "format": schema if use_schema else "json",
        "think": False,
        "keep_alive": "15m",
        "options": {"temperature": 0.2, "num_ctx": 4096, "num_predict": 400, "seed": 42},
    }
    r = requests.post(f"{OLLAMA_URL}/api/chat", json=payload, timeout=timeout)
    if r.status_code != 200 and "think" in r.text.lower():
        # modèle sans mode "thinking" : on relance sans le paramètre
        payload.pop("think")
        r = requests.post(f"{OLLAMA_URL}/api/chat", json=payload, timeout=timeout)
    r.raise_for_status()
    return r.json()


def safe_name(model):
    return re.sub(r"[^A-Za-z0-9._-]", "_", model)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="+", default=DEFAULT_MODELS)
    ap.add_argument("--questions", default="data/questions_eval.json")
    ap.add_argument("--out", default="results")
    ap.add_argument("--no-schema", action="store_true", help="format JSON libre au lieu du schéma imposé")
    ap.add_argument("--limit", type=int, default=0, help="nombre max de questions (test rapide)")
    args = ap.parse_args()

    qfile = json.load(open(args.questions, encoding="utf-8"))
    questions, meta = qfile["questions"], qfile["meta"]
    prompt, schema = build_prompt(meta), build_schema(meta)
    if args.limit:
        questions = questions[: args.limit]
    os.makedirs(args.out, exist_ok=True)

    try:
        tags = [m["name"] for m in requests.get(f"{OLLAMA_URL}/api/tags", timeout=10).json()["models"]]
    except Exception:
        sys.exit(f"Ollama ne répond pas sur {OLLAMA_URL}. Lancez l'application Ollama puis réessayez.")
    missing = [m for m in args.models if m not in tags and f"{m}:latest" not in tags]
    if missing:
        sys.exit(f"Modèles non téléchargés : {missing}\n-> ollama pull <modele>\nDisponibles : {tags}")

    for model in args.models:
        path = os.path.join(args.out, f"raw_{safe_name(model)}.jsonl")
        done = set()
        if os.path.exists(path):
            done = {json.loads(l)["id"] for l in open(path, encoding="utf-8") if l.strip()}
        todo = [q for q in questions if q["id"] not in done]
        print(f"\n=== {model} : {len(todo)} question(s) à traiter ({len(done)} déjà faites) ===")
        if todo:
            print("  chargement du modèle en mémoire...")
            call_ollama(model, "Bonjour", prompt, schema, not args.no_schema)  # échauffement (non mesuré)

        with open(path, "a", encoding="utf-8") as f:
            for i, q in enumerate(todo, 1):
                t0 = time.time()
                try:
                    res = call_ollama(model, q["question"], prompt, schema, not args.no_schema)
                    err = None
                except Exception as e:
                    res, err = {}, str(e)
                content = (res.get("message") or {}).get("content", "")
                parsed = parse_json(content)
                ev_c, ev_d = res.get("eval_count", 0), res.get("eval_duration", 0)
                rec = {
                    "model": model, "id": q["id"], "langue_attendue": q["langue"],
                    "groupe_parallele": q.get("groupe_parallele"),
                    "categorie": q.get("categorie", "base"), "question_d_origine": q.get("question_d_origine"),
                    "intention_attendue": q["intention_attendue"], "profil_attendu": q["profil_attendu"],
                    "question": q["question"], "sortie_brute": content, "sortie": parsed, "erreur": err,
                    "latence_s": round((res.get("total_duration", 0) - res.get("load_duration", 0)) / 1e9, 2)
                                 if res else round(time.time() - t0, 2),
                    "tokens_generes": ev_c,
                    "tokens_par_s": round(ev_c / (ev_d / 1e9), 2) if ev_d else 0,
                }
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                f.flush()
                status = "ERREUR" if err else ("JSON KO" if parsed is None else (parsed.get("intention", "?")))
                print(f"  [{i:>2}/{len(todo)}] {q['id']:<6} {rec['latence_s']:>6.1f}s  {status}")

    print("\nTerminé. Ouvrez maintenant analyse_resultats.ipynb et exécutez toutes les cellules.")


if __name__ == "__main__":
    main()
