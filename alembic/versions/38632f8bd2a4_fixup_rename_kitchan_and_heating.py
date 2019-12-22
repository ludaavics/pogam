"""Fixup of rename kitchen and heating table-objects

Revision ID: 38632f8bd2a4
Revises: c1263c4e9597
Create Date: 2019-12-19 15:45:32.659246

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = "38632f8bd2a4"
down_revision = "c1263c4e9597"
branch_labels = None
depends_on = None


def upgrade():
    op.create_unique_constraint(op.f("uq_heatings_name"), "heatings", ["name"])
    op.drop_constraint("uq_heating_types_name", "heatings", type_="unique")
    op.create_unique_constraint(op.f("uq_kitchens_name"), "kitchens", ["name"])
    op.drop_constraint("uq_kitchen_types_name", "kitchens", type_="unique")


def downgrade():
    op.create_unique_constraint("uq_kitchen_types_name", "kitchens", ["name"])
    op.drop_constraint(op.f("uq_kitchens_name"), "kitchens", type_="unique")
    op.create_unique_constraint("uq_heating_types_name", "heatings", ["name"])
    op.drop_constraint(op.f("uq_heatings_name"), "heatings", type_="unique")
