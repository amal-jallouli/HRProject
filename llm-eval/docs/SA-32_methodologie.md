# SA-32 — Préparation des questions d'évaluation des LLM

**Projet :** SmartCampus AI – Plateforme agentique d'orientation universitaire
**Epic :** Sélection et intégration du LLM

## 1. Objectif

Préparer des requêtes d'admission, d'orientation, des reformulations et des cas ambigus, **avec le français prioritaire**, afin de comparer objectivement plusieurs LLM open-source (SA-33) puis d'évaluer la compréhension du dialecte tunisien et de l'Arabizi par le modèle retenu (SA-34).

## 2. Composition du jeu de test (60 questions)

| Langue | Nombre | Part |
|---|---|---|
| **Français** | **30** | **50 %** |
| Tunisien (écriture arabe) | 10 | 17 % |
| Arabizi | 10 | 17 % |
| Mixte français / tunisien | 10 | 17 % |

| Catégorie | Nombre | Ce qui est testé |
|---|---|---|
| Admission | 6 + questions d'information et de préinscription multilingues | Conditions d'accès, documents, passerelles, test d'entrée, demande de confirmation d'admission |
| Orientation | 4 + questions d'orientation et de profil multilingues | Conseil selon les goûts, la moyenne, les contraintes, le projet professionnel |
| Reformulations | 6 | Même demande formulée autrement que la question d'origine : le modèle doit comprendre la même chose |
| Cas ambigus | 4 | Demandes incomplètes (« C'est combien ? », « Je veux m'inscrire. ») : le modèle doit demander une précision au lieu de deviner |
| Conversation / hors sujet | 7 | Salutations, demandes sans rapport avec l'orientation |

Les questions portent sur les formations réelles de l'IIT (cycle préparatoire, cycle ingénieur en génie informatique, mécanique, télécommunications…, licences appliquées en développement des systèmes TIC, multimédia et web, systèmes embarqués) et de l'ISB (licences en gestion, en administration des affaires, mastères).

## 3. Choix de conception

1. **Français prioritaire** : la moitié du jeu, couvrant toutes les catégories demandées.
2. **Questions parallèles entre langues** : 10 demandes sont posées à la fois en français, en tunisien, en Arabizi et en mixte. Un écart de performance est donc dû à la langue, et non à la question.
3. **Reformulations reliées à leur question d'origine** : on mesure si le modèle reste cohérent quand la même demande est formulée différemment.
4. **Intentions alignées sur le processus métier** (information, comparaison, orientation, profil, préinscription, salutation, hors sujet) : elles serviront au routage de l'agent.
5. **Profil attendu** pour les questions qui contiennent des informations sur le candidat (section, moyenne, intérêts, contraintes), réutilisé par la mémoire conversationnelle.
6. **Comportement attendu** pour chaque question, en particulier : ne jamais inventer de conditions d'admission, ne jamais confirmer une admission, demander une précision en cas d'ambiguïté.
7. **Pas d'évaluation factuelle** : les informations officielles viendront du RAG ; on évalue la compréhension et le comportement du modèle.

## 4. Format de sortie demandé au modèle

```json
{ "langue": "...", "intention": "...", "profil": { }, "reponse": "..." }
```

## 5. Limites

- Jeu de taille réduite, à enrichir avec de vraies demandes de candidats.
- L'orthographe de l'Arabizi n'est pas normalisée : d'autres graphies devront être testées.
