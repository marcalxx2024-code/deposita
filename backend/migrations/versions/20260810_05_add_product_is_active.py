"""Add product activation state for inventory retention.

SQLite supports adding this non-null column with a server default through
``ALTER TABLE ... ADD COLUMN``. Do not use batch mode here: batch mode rebuilds
the table and attempts to drop ``products``, which is unsafe while
``stock_movements`` references it and foreign keys are enforced.

Revision ID: 20260810_05
Revises: 20260809_04
Create Date: 2026-08-10
"""

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision = "20260810_05"
down_revision = "20260809_04"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "products",
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        )
    )


def downgrade() -> None:
    raise RuntimeError(
        "Downgrade de 20260810_05 bloqueado: remover is_active descartaria "
        "o estado de inativacao dos produtos. Restaure um backup ou crie uma "
        "migration de dados explicita se esse rollback for necessario."
    )
