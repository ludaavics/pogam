"""Drop trivial quasi-enum mixins

Revision ID: 7a4074e7d667
Revises: 823af3bb43be
Create Date: 2019-12-27 14:31:39.569024

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "7a4074e7d667"
down_revision = "823af3bb43be"
branch_labels = None
depends_on = None

tables = {
    "listings": [
        ("source", "source_id", "sources", False),
        ("transaction", "transaction_id", "transaction_types", False),
    ],
    "properties": [
        ("heating", "heating_id", "heatings", True),
        ("kitchen", "kitchen_id", "kitchens", True),
        ("type_", "type_id", "property_types", False),
    ],
}


def upgrade():

    conn = op.get_bind()

    for table in tables:
        for name_col, fk_col, enum_table, nullable in tables[table]:
            op.add_column(
                table, sa.Column(name_col, sa.Unicode(length=100), nullable=True)
            )
            conn.execute(
                f"""
                UPDATE "{table}"
                SET "{name_col}" = (
                    SELECT name FROM "{enum_table}"
                    WHERE "{enum_table}".id = "{table}".{fk_col}
                );
                """
            )

            if not nullable:
                op.alter_column(table, name_col, nullable=False)

    op.create_index(op.f("ix_properties_type_"), "properties", ["type_"], unique=False)

    # drop foreign key columns
    op.drop_index("ix_listings_source_id", table_name="listings")
    op.drop_index("ix_properties_heating_id", table_name="properties")
    op.drop_index("ix_properties_kitchen_id", table_name="properties")
    op.drop_index("ix_properties_type_id", table_name="properties")

    op.drop_constraint("fk_listings_source_id_sources", "listings", type_="foreignkey")
    op.drop_constraint(
        "fk_listings_transaction_id_transaction_types", "listings", type_="foreignkey"
    )
    op.drop_constraint(
        "fk_properties_heating_id_heatings", "properties", type_="foreignkey"
    )
    op.drop_constraint(
        "fk_properties_type_id_property_types", "properties", type_="foreignkey"
    )
    op.drop_constraint(
        "fk_properties_kitchen_id_kitchens", "properties", type_="foreignkey"
    )

    op.drop_column("listings", "source_id")
    op.drop_column("listings", "transaction_id")
    op.drop_column("properties", "kitchen_id")
    op.drop_column("properties", "heating_id")
    op.drop_column("properties", "type_id")

    op.drop_table("sources")
    op.drop_table("property_types")
    op.drop_table("kitchens")
    op.drop_table("heatings")
    op.drop_table("transaction_types")


def downgrade():

    # create fk tables
    op.create_table(
        "transaction_types",
        sa.Column("id", sa.INTEGER(), autoincrement=True, nullable=False),
        sa.Column("name", sa.VARCHAR(length=100), autoincrement=False, nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_transaction_types"),
        sa.UniqueConstraint("name", name="uq_transaction_types_name"),
    )
    op.create_table(
        "heatings",
        sa.Column("id", sa.INTEGER(), autoincrement=True, nullable=False),
        sa.Column("name", sa.VARCHAR(length=100), autoincrement=False, nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_heating_types"),
        sa.UniqueConstraint("name", name="uq_heatings_name"),
    )
    op.create_table(
        "kitchens",
        sa.Column("id", sa.INTEGER(), autoincrement=True, nullable=False),
        sa.Column("name", sa.VARCHAR(length=100), autoincrement=False, nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_kitchen_types"),
        sa.UniqueConstraint("name", name="uq_kitchens_name"),
    )
    op.create_table(
        "property_types",
        sa.Column("id", sa.INTEGER(), autoincrement=True, nullable=False),
        sa.Column("name", sa.VARCHAR(length=100), autoincrement=False, nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_property_types"),
        sa.UniqueConstraint("name", name="uq_property_types_name"),
    )
    op.create_table(
        "sources",
        sa.Column("id", sa.INTEGER(), autoincrement=True, nullable=False),
        sa.Column("name", sa.VARCHAR(length=100), autoincrement=False, nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_sources"),
        sa.UniqueConstraint("name", name="uq_sources_name"),
    )

    # create fk columns
    op.add_column(
        "properties",
        sa.Column("type_id", sa.INTEGER(), autoincrement=False, nullable=True),
    )
    op.add_column(
        "properties",
        sa.Column("heating_id", sa.INTEGER(), autoincrement=False, nullable=True),
    )
    op.add_column(
        "properties",
        sa.Column("kitchen_id", sa.INTEGER(), autoincrement=False, nullable=True),
    )
    op.add_column(
        "listings",
        sa.Column("transaction_id", sa.INTEGER(), autoincrement=False, nullable=True),
    )
    op.add_column(
        "listings",
        sa.Column("source_id", sa.INTEGER(), autoincrement=False, nullable=True),
    )

    # populate fk columns
    conn = op.get_bind()
    for table in tables:
        for name_col, fk_col, enum_table, nullable in tables[table]:
            conn.execute(
                f"""
                INSERT INTO "{enum_table}" (name)
                SELECT DISTINCT "{name_col}" FROM "{table}";
                """
            )
            conn.execute(
                f"""
                UPDATE "{table}"
                SET "{fk_col}" = (
                    SELECT id FROM "{enum_table}"
                    WHERE "{enum_table}".name = "{table}".{name_col}
                );
                """
            )
    op.alter_column("properties", "type_id", nullable=False)
    op.alter_column("listings", "transaction_id", nullable=False)

    # add fk constraints
    op.create_foreign_key(
        "fk_properties_type_id_property_types",
        "properties",
        "property_types",
        ["type_id"],
        ["id"],
        onupdate="CASCADE",
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_properties_kitchen_id_kitchens",
        "properties",
        "kitchens",
        ["kitchen_id"],
        ["id"],
        onupdate="CASCADE",
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_properties_heating_id_heatings",
        "properties",
        "heatings",
        ["heating_id"],
        ["id"],
        onupdate="CASCADE",
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_listings_transaction_id_transaction_types",
        "listings",
        "transaction_types",
        ["transaction_id"],
        ["id"],
        onupdate="CASCADE",
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_listings_source_id_sources",
        "listings",
        "sources",
        ["source_id"],
        ["id"],
        onupdate="CASCADE",
        ondelete="CASCADE",
    )

    # add indices
    op.create_index("ix_properties_type_id", "properties", ["type_id"], unique=False)
    op.create_index(
        "ix_properties_kitchen_id", "properties", ["kitchen_id"], unique=False
    )
    op.create_index(
        "ix_properties_heating_id", "properties", ["heating_id"], unique=False
    )
    op.create_index("ix_listings_source_id", "listings", ["source_id"], unique=False)

    # drop columns
    op.drop_index(op.f("ix_properties_type_"), table_name="properties")
    op.drop_column("properties", "type_")
    op.drop_column("properties", "kitchen")
    op.drop_column("properties", "heating")
    op.drop_column("listings", "transaction")
    op.drop_column("listings", "source")
