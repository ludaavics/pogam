"""Add fields from leboncoin

Revision ID: a53aa78ee07c
Revises: 6a6dd6943dce
Create Date: 2019-12-25 20:44:40.361845

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "a53aa78ee07c"
down_revision = "6a6dd6943dce"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "listings",
        sa.Column(
            "broker_fee_is_included", sa.Boolean(create_constraint=False), nullable=True
        ),
    )
    op.add_column(
        "listings", sa.Column("first_publication_date", sa.DateTime(), nullable=True)
    )
    op.add_column(
        "listings",
        sa.Column("is_furnished", sa.Boolean(create_constraint=False), nullable=True),
    )


def downgrade():
    op.drop_column("listings", "is_furnished")
    op.drop_column("listings", "first_publication_date")
    op.drop_column("listings", "broker_fee_is_included")
