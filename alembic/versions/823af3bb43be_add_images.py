"""Add images

Revision ID: 823af3bb43be
Revises: a53aa78ee07c
Create Date: 2019-12-26 21:23:41.607330

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "823af3bb43be"
down_revision = "a53aa78ee07c"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "listings",
        sa.Column("images", postgresql.JSON(astext_type=sa.Text()), nullable=True),
    )


def downgrade():
    op.drop_column("listings", "images")
