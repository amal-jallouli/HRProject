# Sélection du LLM — SmartCampus AI

Epic « Sélection et intégration du LLM » : comparaison de trois LLM open-source exécutés en local (Ollama) afin de choisir le modèle de base du chatbot d'orientation.

| Tâche | Livrables |
|---|---|
| **SA-32** Préparer les questions d'évaluation | `data/` (60 questions : 30 en français, 30 en tunisien, Arabizi et mixte) · `docs/SA-32_methodologie.md` |
| **SA-33** Comparer les performances des modèles LLM | `run_benchmark.py` · `analyse_resultats.ipynb` · `results/` · `docs/SA-33_Comparaison_modeles_LLM.pdf` |
| **SA-34** Dialecte tunisien et Arabizi | Partie SA-34 de `analyse_resultats.ipynb` · `docs/SA-34_Dialecte_tunisien_Arabizi.pdf` |

## Modèles comparés
Gemma 4 E2B (Google) · Qwen 3.5 4B (Alibaba) · Llama 3.2 3B (Meta)

## Métriques
Accuracy · Macro-F1 · Recall · Answer Relevancy · Hallucination Rate · Latency · Throughput · Cost

## Contenu
| Fichier | Rôle |
|---|---|
| `run_benchmark.py` | Envoie les mêmes questions et le même prompt à chaque modèle et enregistre les réponses (`results/raw_*.jsonl`) |
| `analyse_resultats.ipynb` | Calcule les métriques, compare les modèles (français / dialecte), coûts, erreurs, matrices de confusion, score final, analyse SA-34 |
| `results/a_annoter.csv` | Évaluation humaine des 180 réponses (pertinence, registre, hallucination) |
| `results/figures/` | Graphiques produits par le notebook |

## Exécution
```bash
pip install -r requirements.txt
ollama pull gemma4:e2b-it-qat && ollama pull qwen3.5:4b && ollama pull llama3.2:3b
python run_benchmark.py
python run_benchmark.py --questions data/questions_eval_complement_FR.json
jupyter notebook analyse_resultats.ipynb
```
