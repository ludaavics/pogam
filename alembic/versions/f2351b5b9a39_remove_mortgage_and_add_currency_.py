"""Remove mortgage and add currency columns in listings

Revision ID: f2351b5b9a39
Revises: 9479aaac5ade
Create Date: 2019-12-18 07:00:05.913841

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "f2351b5b9a39"
down_revision = "9479aaac5ade"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "listings", sa.Column("currency", sa.Unicode(length=10), nullable=True)
    )
    op.drop_column("listings", "mortgage")


def downgrade():
    op.add_column(
        "listings",
        sa.Column(
            "mortgage",
            postgresql.DOUBLE_PRECISION(precision=53),
            autoincrement=False,
            nullable=True,
        ),
    )
    op.drop_column("listings", "currency")
