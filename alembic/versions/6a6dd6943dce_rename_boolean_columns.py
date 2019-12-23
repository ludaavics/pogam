"""Rename boolean columns

Revision ID: 6a6dd6943dce
Revises: 702b7e7b207d
Create Date: 2019-12-22 19:50:28.810157

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "6a6dd6943dce"
down_revision = "702b7e7b207d"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column("properties", "cellar", new_column_name="has_cellar")
    op.alter_column("properties", "pool", new_column_name="has_pool")
    op.alter_column("properties", "lawn", new_column_name="has_lawn")
    op.alter_column("properties", "super_", new_column_name="has_super")
    op.alter_column("properties", "elevator", new_column_name="has_elevator")
    op.alter_column(
        "properties", "hardwood_floors", new_column_name="has_hardwood_floors"
    )
    op.alter_column("properties", "fireplace", new_column_name="has_fireplace")
    op.alter_column("properties", "view", new_column_name="has_view")


def downgrade():
    op.alter_column("properties", "has_view", new_column_name="view")
    op.alter_column("properties", "has_super", new_column_name="super_")
    op.alter_column("properties", "has_pool", new_column_name="pool")
    op.alter_column("properties", "has_lawn", new_column_name="lawn")
    op.alter_column(
        "properties", "has_hardwood_floors", new_column_name="hardwood_floors"
    )
    op.alter_column("properties", "has_fireplace", new_column_name="fireplace")
    op.alter_column("properties", "has_elevator", new_column_name="elevator")
    op.alter_column("properties", "has_cellar", new_column_name="cellar")
