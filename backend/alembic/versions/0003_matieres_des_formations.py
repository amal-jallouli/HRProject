"""SA-20 : matières des formations (le programme pédagogique = l'ensemble de ses matières).

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "subjects",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("program_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("semester", sa.SmallInteger(), nullable=False),
        sa.Column("credits", sa.SmallInteger(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "credits IS NULL OR credits >= 0", name=op.f("ck_subjects_credits_non_negative")
        ),
        sa.CheckConstraint("semester BETWEEN 1 AND 12", name=op.f("ck_subjects_semester_range")),
        sa.ForeignKeyConstraint(
            ["program_id"],
            ["programs.id"],
            name=op.f("fk_subjects_program_id_programs"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_subjects")),
        sa.UniqueConstraint(
            "program_id", "semester", "name", name=op.f("uq_subjects_program_id_semester_name")
        ),
    )
    op.create_index(op.f("ix_subjects_program_id"), "subjects", ["program_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_subjects_program_id"), table_name="subjects")
    op.drop_table("subjects")
