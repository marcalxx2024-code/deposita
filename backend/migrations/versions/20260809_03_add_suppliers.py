"""Add suppliers and optional product suppliers.

Revision ID: 20260809_03
Revises: 20260809_02
Create Date: 2026-08-09
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260809_03"
down_revision = "20260809_02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "suppliers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("contact_name", sa.String(), nullable=True),
        sa.Column("phone", sa.String(), nullable=True),
        sa.Column("email", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_suppliers_id", "suppliers", ["id"], unique=False)

    op.execute(
        "ALTER TABLE products "
        "ADD COLUMN supplier_id INTEGER REFERENCES suppliers(id)"
    )
    op.create_index("ix_products_supplier_id", "products", ["supplier_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_products_supplier_id", table_name="products")
    op.execute("ALTER TABLE products DROP COLUMN supplier_id")

    op.drop_index("ix_suppliers_id", table_name="suppliers")
    op.drop_table("suppliers")
