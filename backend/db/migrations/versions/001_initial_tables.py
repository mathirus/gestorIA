"""initial tables

Revision ID: 001_initial
Revises:
Create Date: 2026-03-14

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "consultas",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("patente", sa.String(length=10), nullable=False),
        sa.Column("provincia", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_consultas_patente"), "consultas", ["patente"], unique=False)

    op.create_table(
        "sub_consultas",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("consulta_id", sa.Integer(), nullable=False),
        sa.Column(
            "tipo",
            sa.Enum(
                "costos",
                "patentes_caba",
                "patentes_pba",
                "vtv_pba",
                "vtv_caba",
                "multas",
                "dominio",
                name="tipoconsulta",
            ),
            nullable=False,
        ),
        sa.Column(
            "estado",
            sa.Enum(
                "pendiente",
                "ejecutando",
                "completado",
                "fallido",
                "reintentando",
                "pendiente_24hs",
                name="estadoconsulta",
            ),
            nullable=False,
        ),
        sa.Column("intentos", sa.Integer(), nullable=False),
        sa.Column("datos", sa.JSON(), nullable=True),
        sa.Column("error", sa.String(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["consulta_id"], ["consultas.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("sub_consultas")
    op.drop_index(op.f("ix_consultas_patente"), table_name="consultas")
    op.drop_table("consultas")
    op.execute("DROP TYPE IF EXISTS tipoconsulta")
    op.execute("DROP TYPE IF EXISTS estadoconsulta")
