"""Add unique SKUs to products.

Revision ID: 20260809_04
Revises: 20260809_03
Create Date: 2026-08-09
"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "20260809_04"
down_revision = "20260809_03"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE products ADD COLUMN sku VARCHAR NOT NULL "
        "DEFAULT 'LEGACY-UNASSIGNED' CHECK (length(trim(sku)) > 0)"
    )
    op.execute(
        "UPDATE products SET sku = 'LEGACY-' || id "
        "WHERE sku = 'LEGACY-UNASSIGNED'"
    )
    op.create_index("ix_products_sku", "products", ["sku"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_products_sku", table_name="products")
    op.execute("ALTER TABLE products DROP COLUMN sku")
