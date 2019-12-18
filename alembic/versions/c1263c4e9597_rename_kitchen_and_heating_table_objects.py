"""Rename kitchen and heating table-objects

Revision ID: c1263c4e9597
Revises: f2351b5b9a39
Create Date: 2019-12-18 16:50:09.384233

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "c1263c4e9597"
down_revision = "f2351b5b9a39"
branch_labels = None
depends_on = None


def upgrade():
    op.rename_table("heating_types", "heatings")
    op.rename_table("kitchen_types", "kitchens")
    op.drop_constraint(
        "fk_properties_kitchen_id_kitchen_types", "properties", type_="foreignkey"
    )
    op.drop_constraint(
        "fk_properties_heating_id_heating_types", "properties", type_="foreignkey"
    )
    op.create_foreign_key(
        op.f("fk_properties_kitchen_id_kitchens"),
        "properties",
        "kitchens",
        ["kitchen_id"],
        ["id"],
        onupdate="CASCADE",
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        op.f("fk_properties_heating_id_heatings"),
        "properties",
        "heatings",
        ["heating_id"],
        ["id"],
        onupdate="CASCADE",
        ondelete="RESTRICT",
    )


def downgrade():
    op.drop_constraint(
        op.f("fk_properties_heating_id_heatings"), "properties", type_="foreignkey"
    )
    op.drop_constraint(
        op.f("fk_properties_kitchen_id_kitchens"), "properties", type_="foreignkey"
    )
    op.create_foreign_key(
        "fk_properties_heating_id_heating_types",
        "properties",
        "heating_types",
        ["heating_id"],
        ["id"],
        onupdate="CASCADE",
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_properties_kitchen_id_kitchen_types",
        "properties",
        "kitchen_types",
        ["kitchen_id"],
        ["id"],
        onupdate="CASCADE",
        ondelete="RESTRICT",
    )
    op.rename_table("heating_types", "heatings")
    op.rename_table("kitchen_types", "kitchens")
