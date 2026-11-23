"""Données de démonstration SmartCampus AI (SA-18).

Remplit la base avec les institutions (IIT, ISB), leurs formations, les frais et conditions
d'admission par année universitaire, et des comptes responsables de démonstration.

Lancement : ``make db-seed``  (équivalent : ``python -m app.db.seed``)

Le script est IDEMPOTENT : on peut le relancer sans créer de doublons, et il ne modifie
jamais une ligne déjà existante (vos modifications manuelles sont conservées).

ATTENTION - données fictives :
  * La structure (formations, niveaux, filières) s'inspire de l'offre publique de l'IIT et de
    l'ISB (Université Nord-Américaine Privée, Sfax).
  * Les frais, moyennes minimales, durées détaillées et matières (sauf celles du cycle
    préparatoire) sont INDICATIFS : à remplacer par les valeurs officielles.
  * Les comptes de démonstration partagent un mot de passe public : ne jamais déployer tel quel.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

import bcrypt
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models import Institution, Program, ProgramYear, User
from app.models.enums import ProgramLevel, PublicationStatus, UserRole

DEMO_PASSWORD = "Demo@2026"  # mot de passe de TOUS les comptes de démonstration
YEARS = ("2026-2027", "2027-2028")

# Modalités de paiement INDICATIVES
PAYMENT_TERMS = {
    "IIT": "Paiement en 3 tranches : 50 % à l'inscription, 25 % en janvier, 25 % en avril.",
    "ISB": "Paiement par semestre : 50 % à l'inscription, 50 % au début du second semestre.",
}

BAC_SCIENTIFIQUES = [
    "Mathématiques",
    "Sciences expérimentales",
    "Informatique",
    "Sciences techniques",
]
BAC_TOUTES_SECTIONS = [*BAC_SCIENTIFIQUES, "Économie et gestion", "Lettres"]

INSTITUTIONS = {
    "IIT": "Institut International de Technologie",
    "ISB": "International School of Business",
}


@dataclass(frozen=True)
class ProgramSpec:
    institution: str
    name: str
    level: ProgramLevel
    duration_years: int
    description: str
    career_outcomes: str
    skills_tags: list[str]
    bac_sections: list[str] | None
    min_average: Decimal
    tuition: tuple[
        int, int
    ]  # (2026-2027, 2027-2028) en TND : la scolarité augmente chaque année
    registration_fee: int


PROGRAMS: list[ProgramSpec] = [
    # ------------------------------------------------------------------ IIT : cycle préparatoire
    ProgramSpec(
        "IIT",
        "Cycle Préparatoire aux Études d'Ingénieur",
        ProgramLevel.prepa,
        2,
        "Cycle préparatoire de 2 ans (Bac+2) accessible aux bacheliers scientifiques, qui prépare "
        "au cycle ingénieur et aux grandes écoles d'ingénieurs. Matières principales : Analyse, "
        "Algèbre, Physique, Chimie, Informatique, Anglais, Français.",
        "Accès au cycle ingénieur de l'IIT (Génie Informatique, Civil, Industriel, Mécanique, "
        "Procédés) ou aux concours des écoles d'ingénieurs.",
        ["mathématiques", "physique", "chimie", "informatique", "rigueur", "langues"],
        BAC_SCIENTIFIQUES,
        Decimal("12.00"),
        (5800, 6100),
        300,
    ),
    # ------------------------------------------------------------------ IIT : licences informatique
    ProgramSpec(
        "IIT",
        "Licence en Informatique - Réseaux et Cybersécurité",
        ProgramLevel.licence,
        3,
        "Licence en informatique orientée infrastructures réseaux et sécurité. Matières "
        "indicatives : Réseaux, Systèmes d'exploitation, Cryptographie, Sécurité des systèmes, "
        "Administration Linux, Programmation.",
        "Administrateur réseaux, technicien cybersécurité, analyste SOC junior.",
        ["réseaux", "sécurité", "systèmes", "linux", "programmation"],
        BAC_SCIENTIFIQUES,
        Decimal("10.00"),
        (6000, 6300),
        300,
    ),
    ProgramSpec(
        "IIT",
        "Licence en Informatique - Systèmes Embarqués et IoT",
        ProgramLevel.licence,
        3,
        "Licence en informatique centrée sur les systèmes embarqués et l'Internet des objets. "
        "Matières indicatives : Électronique numérique, Microcontrôleurs, C embarqué, Capteurs "
        "et IoT, Systèmes temps réel.",
        "Développeur systèmes embarqués, technicien IoT, intégrateur de solutions connectées.",
        ["embarqué", "électronique", "iot", "c", "microcontrôleurs"],
        BAC_SCIENTIFIQUES,
        Decimal("10.00"),
        (6000, 6300),
        300,
    ),
    ProgramSpec(
        "IIT",
        "Licence en Informatique - Big Data et Data Analytics",
        ProgramLevel.licence,
        3,
        "Licence en informatique tournée vers l'analyse de données. Matières indicatives : "
        "Python, Bases de données, Statistiques, Big Data, Visualisation de données, "
        "Introduction au Machine Learning.",
        "Analyste de données, développeur data, assistant data scientist.",
        ["données", "python", "statistiques", "sql", "machine learning"],
        BAC_SCIENTIFIQUES,
        Decimal("10.50"),
        (6000, 6300),
        300,
    ),
    ProgramSpec(
        "IIT",
        "Licence en Informatique - Génie Logiciel et Systèmes Intelligents",
        ProgramLevel.licence,
        3,
        "Licence en informatique axée sur le développement logiciel et l'intelligence "
        "artificielle appliquée. Matières indicatives : Algorithmique, Programmation orientée "
        "objet, Développement web, Génie logiciel, Bases de données, Intelligence artificielle.",
        "Développeur logiciel, développeur web, ingénieur logiciel junior.",
        ["développement", "algorithmique", "web", "génie logiciel", "ia"],
        BAC_SCIENTIFIQUES,
        Decimal("10.00"),
        (6000, 6300),
        300,
    ),
    # ---------------------------------------------------------- IIT : licences technologiques
    ProgramSpec(
        "IIT",
        "Licence Technologique - Systèmes Électriques Intelligents et Énergies Renouvelables",
        ProgramLevel.licence,
        3,
        "Licence technologique consacrée aux réseaux électriques intelligents et aux énergies "
        "renouvelables. Matières indicatives : Électrotechnique, Électronique de puissance, "
        "Énergie solaire et éolienne, Automatique, Smart grids.",
        "Technicien supérieur en énergies renouvelables, chargé de maintenance électrique.",
        ["électricité", "énergie", "automatique", "renouvelable"],
        BAC_SCIENTIFIQUES,
        Decimal("10.00"),
        (6000, 6300),
        300,
    ),
    ProgramSpec(
        "IIT",
        "Licence Technologique - Mécatronique et Systèmes Intelligents",
        ProgramLevel.licence,
        3,
        "Licence technologique associant mécanique, électronique et informatique. Matières "
        "indicatives : Mécanique, Électronique, Automatique, Robotique, Capteurs et actionneurs, "
        "Programmation de systèmes.",
        "Technicien mécatronicien, intégrateur de systèmes automatisés, maintenance industrielle.",
        ["mécatronique", "robotique", "automatique", "mécanique", "électronique"],
        BAC_SCIENTIFIQUES,
        Decimal("10.00"),
        (6000, 6300),
        300,
    ),
    # ------------------------------------------------------------------ IIT : filières ingénieur
    ProgramSpec(
        "IIT",
        "Cycle Ingénieur - Génie Informatique",
        ProgramLevel.ingenierie,
        3,
        "Diplôme national d'ingénieur en Génie Informatique (3 ans), accessible après le cycle "
        "préparatoire, une licence ou par concours. Matières indicatives : Architecture "
        "logicielle, Cloud et DevOps, Intelligence artificielle, Cybersécurité, Gestion de projet.",
        "Ingénieur logiciel, architecte cloud, ingénieur data/IA, chef de projet informatique.",
        ["logiciel", "cloud", "ia", "architecture", "gestion de projet"],
        None,
        Decimal("12.00"),
        (7500, 7900),
        400,
    ),
    ProgramSpec(
        "IIT",
        "Cycle Ingénieur - Génie Civil",
        ProgramLevel.ingenierie,
        3,
        "Diplôme national d'ingénieur en Génie Civil (3 ans), accessible après le cycle "
        "préparatoire, une licence ou par concours. Matières indicatives : Résistance des "
        "matériaux, Béton armé, Géotechnique, Hydraulique, Gestion de chantier.",
        "Ingénieur bâtiment et travaux publics, ingénieur structures, conducteur de travaux.",
        ["structures", "construction", "géotechnique", "chantier"],
        None,
        Decimal("12.00"),
        (7500, 7900),
        400,
    ),
    ProgramSpec(
        "IIT",
        "Cycle Ingénieur - Génie Industriel",
        ProgramLevel.ingenierie,
        3,
        "Diplôme national d'ingénieur en Génie Industriel (3 ans), accessible après le cycle "
        "préparatoire, une licence ou par concours. Matières indicatives : Recherche "
        "opérationnelle, Logistique, Gestion de production, Qualité, Lean management.",
        "Ingénieur méthodes, responsable logistique, ingénieur qualité, responsable production.",
        ["production", "logistique", "qualité", "optimisation", "lean"],
        None,
        Decimal("12.00"),
        (7500, 7900),
        400,
    ),
    ProgramSpec(
        "IIT",
        "Cycle Ingénieur - Génie Mécanique",
        ProgramLevel.ingenierie,
        3,
        "Diplôme national d'ingénieur en Génie Mécanique (3 ans), accessible après le cycle "
        "préparatoire, une licence ou par concours. Matières indicatives : Conception assistée par "
        "ordinateur, Résistance des matériaux, Thermique, Fabrication, Maintenance.",
        "Ingénieur conception, ingénieur de maintenance, ingénieur fabrication.",
        ["conception", "mécanique", "fabrication", "thermique", "maintenance"],
        None,
        Decimal("12.00"),
        (7500, 7900),
        400,
    ),
    ProgramSpec(
        "IIT",
        "Cycle Ingénieur - Génie des Procédés",
        ProgramLevel.ingenierie,
        3,
        "Diplôme national d'ingénieur en Génie des Procédés (3 ans), accessible après le cycle "
        "préparatoire, une licence ou par concours. Matières indicatives : Thermodynamique, "
        "Transferts de chaleur et de matière, Réacteurs chimiques, Environnement, Sécurité "
        "industrielle.",
        "Ingénieur procédés, ingénieur environnement, responsable HSE, ingénieur de production.",
        [
            "procédés",
            "chimie",
            "environnement",
            "thermodynamique",
            "sécurité industrielle",
        ],
        None,
        Decimal("12.00"),
        (7500, 7900),
        400,
    ),
    # ------------------------------------------------------------------ ISB : licences
    ProgramSpec(
        "ISB",
        "Licence Fondamentale en Gestion",
        ProgramLevel.licence,
        3,
        "Licence nationale de gestion (3 ans) en français. Matières indicatives : Comptabilité, "
        "Management, Marketing, Finance, Statistiques, Droit des affaires.",
        "Poursuite en mastère, assistant de gestion, collaborateur financier ou commercial.",
        ["gestion", "comptabilité", "management", "finance", "marketing"],
        BAC_TOUTES_SECTIONS,
        Decimal("10.00"),
        (4800, 5100),
        250,
    ),
    ProgramSpec(
        "ISB",
        "Licence Fondamentale en Administration des Affaires (en anglais)",
        ProgramLevel.licence,
        3,
        "Licence en administration des affaires (3 ans) enseignée en anglais, selon le modèle "
        "nord-américain. Matières indicatives : Business Management, Accounting, Marketing, "
        "Finance, Business Communication.",
        "Poursuite en MBA ou mastère, carrière en entreprise internationale.",
        ["business", "anglais", "management", "marketing", "finance"],
        BAC_TOUTES_SECTIONS,
        Decimal("10.50"),
        (5200, 5500),
        250,
    ),
    ProgramSpec(
        "ISB",
        "Licence Fondamentale en Droit Privé",
        ProgramLevel.licence,
        3,
        "Licence fondamentale en droit privé (3 ans). Matières indicatives : Droit civil, Droit "
        "commercial, Droit des obligations, Procédure civile, Droit du travail.",
        "Poursuite en mastère de droit, juriste d'entreprise, carrières judiciaires et juridiques.",
        ["droit", "rédaction", "argumentation", "analyse juridique"],
        BAC_TOUTES_SECTIONS,
        Decimal("10.00"),
        (4800, 5100),
        250,
    ),
    # ------------------------------------------------------------------ ISB : mastères et MBA
    ProgramSpec(
        "ISB",
        "Mastère Professionnel en Marketing",
        ProgramLevel.autre,
        2,
        "Mastère professionnel de 2 ans, accessible après une licence. Matières indicatives : "
        "Marketing stratégique, Marketing digital, Études de marché, Comportement du consommateur.",
        "Responsable marketing, chef de produit, responsable marketing digital.",
        ["marketing", "digital", "stratégie", "études de marché"],
        None,
        Decimal("12.00"),
        (5500, 5800),
        300,
    ),
    ProgramSpec(
        "ISB",
        "Mastère Professionnel en Comptabilité",
        ProgramLevel.autre,
        2,
        "Mastère professionnel de 2 ans, accessible après une licence. Matières indicatives : "
        "Comptabilité approfondie, Audit, Fiscalité, Contrôle de gestion.",
        "Comptable, auditeur junior, contrôleur de gestion, préparation à l'expertise comptable.",
        ["comptabilité", "audit", "fiscalité", "contrôle de gestion"],
        None,
        Decimal("12.00"),
        (5500, 5800),
        300,
    ),
    ProgramSpec(
        "ISB",
        "Master of Business Administration (MBA)",
        ProgramLevel.autre,
        2,
        "MBA de 2 ans enseigné à 100 % en anglais, avec séminaires, ateliers et intervenants "
        "internationaux. Matières indicatives : Strategic Management, Leadership, Corporate "
        "Finance, Marketing Management, Entrepreneurship.",
        "Cadre dirigeant, responsable de département, entrepreneur.",
        ["leadership", "stratégie", "anglais", "entrepreneuriat", "finance"],
        None,
        Decimal("12.00"),
        (8000, 8400),
        400,
    ),
]

DEMO_USERS: list[tuple[str, str, UserRole, str | None]] = [
    ("admin@smartcampus.tn", "Administrateur Démo", UserRole.admin, None),
    ("resp.iit@smartcampus.tn", "Responsable Académique IIT", UserRole.academic, "IIT"),
    ("resp.isb@smartcampus.tn", "Responsable Académique ISB", UserRole.academic, "ISB"),
    ("entretien@smartcampus.tn", "Responsable Entretien", UserRole.interviewer, None),
]


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def seed(session: Session) -> dict[str, int]:
    """Insère les données manquantes ; retourne le nombre de lignes créées par table."""
    created = {"institutions": 0, "programs": 0, "program_years": 0, "users": 0}

    # --- Institutions
    institutions: dict[str, Institution] = {}
    for code, name in INSTITUTIONS.items():
        inst = session.scalar(select(Institution).where(Institution.code == code))
        if inst is None:
            inst = Institution(code=code, name=name)
            session.add(inst)
            session.flush()
            created["institutions"] += 1
        institutions[code] = inst

    # --- Formations + frais/conditions par année
    for spec in PROGRAMS:
        inst = institutions[spec.institution]
        program = session.scalar(
            select(Program).where(
                Program.institution_id == inst.id, Program.name == spec.name
            )
        )
        if program is None:
            program = Program(
                institution_id=inst.id,
                name=spec.name,
                level=spec.level,
                description=spec.description,
                duration_years=spec.duration_years,
                career_outcomes=spec.career_outcomes,
                skills_tags=spec.skills_tags,
            )
            session.add(program)
            session.flush()
            created["programs"] += 1

        for year, tuition in zip(YEARS, spec.tuition, strict=True):
            exists = session.scalar(
                select(ProgramYear.id).where(
                    ProgramYear.program_id == program.id,
                    ProgramYear.academic_year == year,
                )
            )
            if exists is None:
                session.add(
                    ProgramYear(
                        program_id=program.id,
                        academic_year=year,
                        tuition_amount=Decimal(tuition),
                        registration_fee=Decimal(spec.registration_fee),
                        min_average=spec.min_average,
                        bac_sections=spec.bac_sections,
                        payment_terms=PAYMENT_TERMS[spec.institution],
                        status=PublicationStatus.published,
                        # offre valable de juin (ouverture des inscriptions) à fin août de l'année
                        valid_from=date(int(year[:4]), 6, 1),
                        valid_until=date(int(year[5:]), 8, 31),
                    )
                )
                created["program_years"] += 1

    # --- Comptes responsables (mot de passe haché avec bcrypt)
    for email, full_name, role, inst_code in DEMO_USERS:
        if session.scalar(select(User.id).where(User.email == email)) is None:
            session.add(
                User(
                    email=email,
                    password_hash=_hash_password(DEMO_PASSWORD),
                    full_name=full_name,
                    role=role,
                    institution_id=institutions[inst_code].id if inst_code else None,
                )
            )
            created["users"] += 1

    session.commit()
    return created


def main() -> None:
    with SessionLocal() as session:
        created = seed(session)
    print("Données de démonstration insérées (0 = déjà présentes) :")
    for table, count in created.items():
        print(f"  {table:<15} +{count}")
    print(f"\nComptes de démonstration - mot de passe commun : {DEMO_PASSWORD}")
    for email, _, role, _ in DEMO_USERS:
        print(f"  {role.value:<12} {email}")


if __name__ == "__main__":
    main()
