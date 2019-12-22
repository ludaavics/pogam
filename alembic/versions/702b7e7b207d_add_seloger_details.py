"""Add seloger details

Revision ID: 702b7e7b207d
Revises: 38632f8bd2a4
Create Date: 2019-12-21 15:02:56.250395

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "702b7e7b207d"
down_revision = "38632f8bd2a4"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("listings", sa.Column("broker_fee", sa.Float(), nullable=True))
    op.add_column("listings", sa.Column("security_deposit", sa.Float(), nullable=True))
    op.add_column(
        "properties",
        sa.Column("cellar", sa.Boolean(create_constraint=False), nullable=True),
    )
    op.add_column(
        "properties",
        sa.Column("elevator", sa.Boolean(create_constraint=False), nullable=True),
    )
    op.add_column(
        "properties", sa.Column("exposure", sa.Unicode(length=50), nullable=True)
    )
    op.add_column(
        "properties",
        sa.Column("fireplace", sa.Boolean(create_constraint=False), nullable=True),
    )
    op.add_column(
        "properties",
        sa.Column(
            "hardwood_floors", sa.Boolean(create_constraint=False), nullable=True
        ),
    )
    op.add_column(
        "properties",
        sa.Column("lawn", sa.Boolean(create_constraint=False), nullable=True),
    )
    op.add_column("properties", sa.Column("parkings", sa.Integer(), nullable=True))
    op.add_column(
        "properties",
        sa.Column("pool", sa.Boolean(create_constraint=False), nullable=True),
    )
    op.add_column(
        "properties",
        sa.Column("super_", sa.Boolean(create_constraint=False), nullable=True),
    )
    op.add_column("properties", sa.Column("terraces", sa.Integer(), nullable=True))
    op.add_column(
        "properties",
        sa.Column("view", sa.Boolean(create_constraint=False), nullable=True),
    )


def downgrade():
    op.drop_column("properties", "view")
    op.drop_column("properties", "terraces")
    op.drop_column("properties", "super_")
    op.drop_column("properties", "pool")
    op.drop_column("properties", "parkings")
    op.drop_column("properties", "lawn")
    op.drop_column("properties", "hardwood_floors")
    op.drop_column("properties", "fireplace")
    op.drop_column("properties", "exposure")
    op.drop_column("properties", "elevator")
    op.drop_column("properties", "cellar")
    op.drop_column("listings", "security_deposit")
    op.drop_column("listings", "broker_fee")
