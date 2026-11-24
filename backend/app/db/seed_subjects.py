"""Matières de démonstration par formation (SA-20) : (semestre, matière, crédits).

DONNÉES FICTIVES et INDICATIVES : à remplacer par les programmes pédagogiques officiels.
Chaque formation = un tronc commun de sa famille + ses matières de spécialité.
"""

Subj = tuple[int, str, int]

_CORE_INFO: list[Subj] = [
    (1, "Algorithmique et programmation", 6),
    (1, "Analyse mathématique", 5),
    (1, "Architecture des ordinateurs", 4),
    (1, "Anglais technique", 2),
    (2, "Bases de données", 5),
    (2, "Programmation orientée objet", 6),
    (2, "Réseaux informatiques", 4),
    (2, "Probabilités et statistiques", 4),
]
_CORE_TECHNO: list[Subj] = [
    (1, "Mathématiques pour l'ingénieur", 5),
    (1, "Physique générale", 5),
    (1, "Algorithmique et programmation", 4),
    (1, "Anglais technique", 2),
    (2, "Électricité générale", 5),
    (2, "Dessin technique et CAO", 4),
    (2, "Automatique de base", 4),
    (2, "Communication professionnelle", 2),
]
_CORE_ENGINEER: list[Subj] = [
    (1, "Mathématiques appliquées", 4),
    (1, "Management de projet", 3),
    (1, "Anglais professionnel", 2),
    (2, "Méthodes numériques", 4),
    (2, "Entrepreneuriat et innovation", 2),
]
_CORE_ISB: list[Subj] = [
    (1, "Introduction à la gestion", 5),
    (1, "Comptabilité générale", 5),
    (1, "Microéconomie", 4),
    (1, "Anglais des affaires", 3),
    (2, "Marketing fondamental", 4),
    (2, "Macroéconomie", 4),
    (2, "Statistiques appliquées à la gestion", 4),
    (2, "Droit des affaires", 3),
]

_SPECIFIC: dict[str, list[Subj]] = {
    "Cycle Préparatoire aux Études d'Ingénieur": [
        (1, "Analyse 1", 6),
        (1, "Algèbre 1", 5),
        (1, "Physique 1 : mécanique du point", 5),
        (1, "Chimie générale", 4),
        (1, "Informatique 1", 3),
        (1, "Langue française", 2),
        (2, "Analyse 2", 6),
        (2, "Algèbre 2", 5),
        (2, "Physique 2 : électricité", 5),
        (2, "Thermodynamique", 4),
        (2, "Informatique 2", 3),
        (2, "Anglais", 2),
        (3, "Analyse 3", 6),
        (3, "Physique 3 : optique et ondes", 5),
        (3, "Mécanique du solide", 4),
        (3, "Probabilités", 4),
        (4, "Équations différentielles", 5),
        (4, "Électromagnétisme", 5),
        (4, "Mécanique des fluides", 4),
        (4, "Statistiques", 4),
    ],
    "Licence en Informatique - Réseaux et Cybersécurité": [
        (3, "Administration des systèmes Linux", 5),
        (3, "Routage et commutation", 5),
        (4, "Sécurité des réseaux", 6),
        (5, "Cryptographie appliquée", 5),
        (5, "Tests d'intrusion", 5),
        (6, "Supervision et gestion des incidents", 4),
    ],
    "Licence en Informatique - Systèmes Embarqués et IoT": [
        (3, "Microcontrôleurs et systèmes temps réel", 6),
        (3, "Électronique numérique", 5),
        (4, "Protocoles IoT et capteurs", 5),
        (5, "Linux embarqué", 5),
        (5, "Cloud pour l'IoT", 4),
        (6, "Projet de fin d'études IoT", 8),
    ],
    "Licence en Informatique - Big Data et Data Analytics": [
        (3, "Fouille de données", 5),
        (3, "Entrepôts de données", 5),
        (4, "Apprentissage automatique", 6),
        (5, "Technologies Big Data (Hadoop, Spark)", 6),
        (5, "Visualisation de données", 4),
        (6, "Projet de fin d'études en data", 8),
    ],
    "Licence en Informatique - Génie Logiciel et Systèmes Intelligents": [
        (3, "Conception UML et architectures logicielles", 5),
        (3, "Développement web et mobile", 5),
        (4, "Intelligence artificielle", 6),
        (5, "DevOps et tests logiciels", 5),
        (5, "Apprentissage profond", 5),
        (6, "Projet de fin d'études en génie logiciel", 8),
    ],
    "Licence Technologique - Systèmes Électriques Intelligents et Énergies Renouvelables": [
        (3, "Machines électriques", 5),
        (3, "Électronique de puissance", 5),
        (4, "Énergie solaire photovoltaïque", 5),
        (5, "Réseaux électriques intelligents", 5),
        (5, "Efficacité énergétique", 4),
        (6, "Projet de fin d'études en énergie", 8),
    ],
    "Licence Technologique - Mécatronique et Systèmes Intelligents": [
        (3, "Capteurs et actionneurs", 5),
        (3, "Résistance des matériaux", 4),
        (4, "Robotique industrielle", 6),
        (5, "Automates programmables", 5),
        (5, "Vision par ordinateur", 4),
        (6, "Projet de fin d'études en mécatronique", 8),
    ],
    "Cycle Ingénieur - Génie Informatique": [
        (3, "Architecture logicielle avancée", 5),
        (3, "Systèmes distribués", 5),
        (4, "Intelligence artificielle avancée", 6),
        (5, "Cloud computing et DevOps", 5),
        (6, "Projet de fin d'études ingénieur", 15),
    ],
    "Cycle Ingénieur - Génie Civil": [
        (3, "Béton armé", 5),
        (3, "Mécanique des sols", 5),
        (4, "Structures métalliques", 5),
        (5, "Routes et ouvrages d'art", 5),
        (6, "Projet de fin d'études ingénieur", 15),
    ],
    "Cycle Ingénieur - Génie Industriel": [
        (3, "Recherche opérationnelle", 5),
        (3, "Gestion de la production", 5),
        (4, "Gestion de la qualité", 4),
        (5, "Logistique et chaîne d'approvisionnement", 5),
        (6, "Projet de fin d'études ingénieur", 15),
    ],
    "Cycle Ingénieur - Génie Mécanique": [
        (3, "Conception mécanique assistée par ordinateur", 5),
        (3, "Thermodynamique appliquée", 5),
        (4, "Fabrication et usinage", 5),
        (5, "Éléments finis", 5),
        (6, "Projet de fin d'études ingénieur", 15),
    ],
    "Cycle Ingénieur - Génie des Procédés": [
        (3, "Opérations unitaires", 5),
        (3, "Cinétique et réacteurs chimiques", 5),
        (4, "Transfert de chaleur et de matière", 5),
        (5, "Sécurité et environnement industriel", 4),
        (6, "Projet de fin d'études ingénieur", 15),
    ],
    "Licence Fondamentale en Gestion": [
        (3, "Gestion financière", 5),
        (3, "Gestion des ressources humaines", 4),
        (4, "Contrôle de gestion", 5),
        (5, "Management stratégique", 5),
        (6, "Projet de fin d'études en gestion", 8),
    ],
    "Licence Fondamentale en Administration des Affaires (en anglais)": [
        (3, "Corporate Finance", 5),
        (3, "Organizational Behavior", 4),
        (4, "International Business", 5),
        (5, "Operations Management", 5),
        (6, "Capstone Project", 8),
    ],
    "Licence Fondamentale en Droit Privé": [
        (3, "Droit civil : les obligations", 6),
        (3, "Droit commercial", 5),
        (4, "Droit du travail", 5),
        (5, "Procédure civile", 5),
        (6, "Mémoire de fin d'études en droit", 8),
    ],
    "Mastère Professionnel en Marketing": [
        (1, "Stratégie marketing", 6),
        (1, "Comportement du consommateur", 5),
        (2, "Marketing digital", 6),
        (2, "Études de marché", 5),
        (3, "Gestion de marque", 5),
        (4, "Mémoire de mastère", 20),
    ],
    "Mastère Professionnel en Comptabilité": [
        (1, "Comptabilité approfondie", 6),
        (1, "Fiscalité des entreprises", 5),
        (2, "Audit et commissariat aux comptes", 6),
        (2, "Normes comptables internationales", 5),
        (3, "Consolidation des comptes", 5),
        (4, "Mémoire de mastère", 20),
    ],
    "Master of Business Administration (MBA)": [
        (1, "Leadership and Management", 6),
        (1, "Managerial Accounting", 5),
        (2, "Strategic Management", 6),
        (2, "Financial Markets", 5),
        (3, "Entrepreneurship", 5),
        (4, "Final Thesis", 20),
    ],
}

# Familles de formations qui partagent un tronc commun (les mastères / le MBA n'en ont pas)
_CORE_BY_PROGRAM: dict[str, list[Subj]] = {
    **{name: _CORE_INFO for name in _SPECIFIC if name.startswith("Licence en Informatique")},
    **{name: _CORE_TECHNO for name in _SPECIFIC if name.startswith("Licence Technologique")},
    **{name: _CORE_ENGINEER for name in _SPECIFIC if name.startswith("Cycle Ingénieur")},
    **{name: _CORE_ISB for name in _SPECIFIC if name.startswith("Licence Fondamentale")},
}


def subjects_for(program_name: str) -> list[Subj]:
    return [*_CORE_BY_PROGRAM.get(program_name, []), *_SPECIFIC.get(program_name, [])]
