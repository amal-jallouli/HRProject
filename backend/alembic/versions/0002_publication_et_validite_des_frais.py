"""SA-21 : publication, période de validité et modalités de paiement des frais.

Ajoute à `program_years` : payment_terms, status (draft/published/archived), valid_from,
valid_until (+ contrainte d'ordre des dates) et rend unique le nom d'une formation par
institution.

Les lignes déjà présentes passent en `draft` : rien n'est publié par accident, le
responsable académique publie explicitement (POST .../publish).

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# create_type=False : le type est créé explicitement ci-dessous (add_column ne le crée pas)
publication_status = postgresql.ENUM(
    "draft", "published", "archived", name="publication_status", create_type=False
)


def upgrade() -> None:
    publication_status.create(op.get_bind(), checkfirst=True)

    op.add_column("program_years", sa.Column("payment_terms", sa.Text(), nullable=True))
    op.add_column(
        "program_years",
        sa.Column("status", publication_status, server_default="draft", nullable=False),
    )
    op.add_column("program_years", sa.Column("valid_from", sa.Date(), nullable=True))
    op.add_column("program_years", sa.Column("valid_until", sa.Date(), nullable=True))
    op.create_check_constraint(
        op.f("ck_program_years_valid_period_order"),
        "program_years",
        "valid_until IS NULL OR valid_from IS NULL OR valid_until >= valid_from",
    )
    op.create_unique_constraint(
        op.f("uq_programs_institution_id_name"), "programs", ["institution_id", "name"]
    )


def downgrade() -> None:
    op.drop_constraint(op.f("uq_programs_institution_id_name"), "programs", type_="unique")
    op.drop_constraint(op.f("ck_program_years_valid_period_order"), "program_years", type_="check")
    op.drop_column("program_years", "valid_until")
    op.drop_column("program_years", "valid_from")
    op.drop_column("program_years", "status")
    op.drop_column("program_years", "payment_terms")
    op.execute("DROP TYPE IF EXISTS publication_status")
