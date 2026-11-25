"""Créneaux d'entretien : le responsable d'entretien publie ses disponibilités.

Ajoute `interviewer_slots` et relie un rendez-vous à son créneau (`appointments.slot_id`).
Un index unique partiel interdit deux rendez-vous non annulés sur le même créneau ;
annuler un rendez-vous libère donc le créneau.

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "interviewer_slots",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("interviewer_id", sa.UUID(), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "ends_at > starts_at", name=op.f("ck_interviewer_slots_ends_after_starts")
        ),
        sa.ForeignKeyConstraint(
            ["interviewer_id"],
            ["users.id"],
            name=op.f("fk_interviewer_slots_interviewer_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_interviewer_slots")),
        sa.UniqueConstraint(
            "interviewer_id",
            "starts_at",
            name=op.f("uq_interviewer_slots_interviewer_id_starts_at"),
        ),
    )
    op.create_index(
        op.f("ix_interviewer_slots_interviewer_id"), "interviewer_slots", ["interviewer_id"]
    )
    op.create_index(op.f("ix_interviewer_slots_starts_at"), "interviewer_slots", ["starts_at"])

    op.add_column("appointments", sa.Column("slot_id", sa.UUID(), nullable=True))
    op.create_foreign_key(
        op.f("fk_appointments_slot_id_interviewer_slots"),
        "appointments",
        "interviewer_slots",
        ["slot_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "uq_appointments_active_slot",
        "appointments",
        ["slot_id"],
        unique=True,
        postgresql_where=sa.text("status <> 'cancelled'"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_appointments_active_slot",
        table_name="appointments",
        postgresql_where=sa.text("status <> 'cancelled'"),
    )
    op.drop_constraint(
        op.f("fk_appointments_slot_id_interviewer_slots"), "appointments", type_="foreignkey"
    )
    op.drop_column("appointments", "slot_id")
    op.drop_index(op.f("ix_interviewer_slots_starts_at"), table_name="interviewer_slots")
    op.drop_index(op.f("ix_interviewer_slots_interviewer_id"), table_name="interviewer_slots")
    op.drop_table("interviewer_slots")
