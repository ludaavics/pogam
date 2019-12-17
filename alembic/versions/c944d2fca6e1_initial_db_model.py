"""Initial db model

Revision ID: c944d2fca6e1
Revises:
Create Date: 2019-12-16 19:40:16.636937

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "c944d2fca6e1"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "cities",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.Unicode(length=100), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_cities")),
        sa.UniqueConstraint("name", name=op.f("uq_cities_name")),
    )
    op.create_table(
        "heating_types",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.Unicode(length=100), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_heating_types")),
        sa.UniqueConstraint("name", name=op.f("uq_heating_types_name")),
    )
    op.create_table(
        "kitchen_types",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.Unicode(length=100), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_kitchen_types")),
        sa.UniqueConstraint("name", name=op.f("uq_kitchen_types_name")),
    )
    op.create_table(
        "property_types",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.Unicode(length=100), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_property_types")),
        sa.UniqueConstraint("name", name=op.f("uq_property_types_name")),
    )
    op.create_table(
        "sources",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.Unicode(length=100), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sources")),
        sa.UniqueConstraint("name", name=op.f("uq_sources_name")),
    )
    op.create_table(
        "transaction_types",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.Unicode(length=100), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_transaction_types")),
        sa.UniqueConstraint("name", name=op.f("uq_transaction_types_name")),
    )
    op.create_table(
        "neighborhoods",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.Unicode(length=100), nullable=True),
        sa.Column("city_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["city_id"],
            ["cities.id"],
            name=op.f("fk_neighborhoods_city_id_cities"),
            onupdate="CASCADE",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_neighborhoods")),
        sa.UniqueConstraint("name", name=op.f("uq_neighborhoods_name")),
    )
    op.create_index(
        op.f("ix_neighborhoods_city_id"), "neighborhoods", ["city_id"], unique=False
    )
    op.create_table(
        "properties",
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("type_id", sa.Integer(), nullable=True),
        sa.Column("size", sa.Float(), nullable=True),
        sa.Column("floor", sa.Integer(), nullable=True),
        sa.Column("floors", sa.Integer(), nullable=True),
        sa.Column("rooms", sa.Float(), nullable=True),
        sa.Column("bedrooms", sa.Float(), nullable=True),
        sa.Column("bathrooms", sa.Float(), nullable=True),
        sa.Column("balconies", sa.Integer(), nullable=True),
        sa.Column("heating_id", sa.Integer(), nullable=True),
        sa.Column("kitchen_id", sa.Integer(), nullable=True),
        sa.Column("dpe_consumption", sa.Integer(), nullable=True),
        sa.Column("dpe_emissions", sa.Integer(), nullable=True),
        sa.Column("postal_code", sa.Unicode(length=50), nullable=True),
        sa.Column("city_id", sa.Integer(), nullable=True),
        sa.Column("neighborhood_id", sa.Integer(), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("north_east_lat", sa.Float(), nullable=True),
        sa.Column("north_east_long", sa.Float(), nullable=True),
        sa.Column("south_west_lat", sa.Float(), nullable=True),
        sa.Column("south_west_long", sa.Float(), nullable=True),
        sa.Column("map_poly", sa.Unicode(length=100000), nullable=True),
        sa.ForeignKeyConstraint(
            ["city_id"],
            ["cities.id"],
            name=op.f("fk_properties_city_id_cities"),
            onupdate="CASCADE",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["heating_id"],
            ["heating_types.id"],
            name=op.f("fk_properties_heating_id_heating_types"),
            onupdate="CASCADE",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["kitchen_id"],
            ["kitchen_types.id"],
            name=op.f("fk_properties_kitchen_id_kitchen_types"),
            onupdate="CASCADE",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["neighborhood_id"],
            ["neighborhoods.id"],
            name=op.f("fk_properties_neighborhood_id_neighborhoods"),
            onupdate="CASCADE",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["type_id"],
            ["property_types.id"],
            name=op.f("fk_properties_type_id_property_types"),
            onupdate="CASCADE",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_properties")),
    )
    op.create_index(
        op.f("ix_properties_city_id"), "properties", ["city_id"], unique=False
    )
    op.create_index(
        op.f("ix_properties_heating_id"), "properties", ["heating_id"], unique=False
    )
    op.create_index(
        op.f("ix_properties_kitchen_id"), "properties", ["kitchen_id"], unique=False
    )
    op.create_index(
        op.f("ix_properties_neighborhood_id"),
        "properties",
        ["neighborhood_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_properties_type_id"), "properties", ["type_id"], unique=False
    )
    op.create_table(
        "listings",
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("property_id", sa.Integer(), nullable=True),
        sa.Column("source_id", sa.Integer(), nullable=True),
        sa.Column("url", sa.Unicode(length=10000), nullable=True),
        sa.Column("transaction_id", sa.Integer(), nullable=False),
        sa.Column("description", sa.Unicode(length=10000000), nullable=True),
        sa.Column("price", sa.Float(), nullable=True),
        sa.Column("mortgage", sa.Float(), nullable=True),
        sa.Column("external_listing_id", sa.Unicode(length=200), nullable=True),
        sa.ForeignKeyConstraint(
            ["property_id"],
            ["properties.id"],
            name=op.f("fk_listings_property_id_properties"),
            onupdate="CASCADE",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["sources.id"],
            name=op.f("fk_listings_source_id_sources"),
            onupdate="CASCADE",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["transaction_id"],
            ["transaction_types.id"],
            name=op.f("fk_listings_transaction_id_transaction_types"),
            onupdate="CASCADE",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_listings")),
    )
    op.create_index(
        op.f("ix_listings_property_id"), "listings", ["property_id"], unique=False
    )
    op.create_index(
        op.f("ix_listings_source_id"), "listings", ["source_id"], unique=False
    )


def downgrade():
    op.drop_index(op.f("ix_listings_source_id"), table_name="listings")
    op.drop_index(op.f("ix_listings_property_id"), table_name="listings")
    op.drop_table("listings")
    op.drop_index(op.f("ix_properties_type_id"), table_name="properties")
    op.drop_index(op.f("ix_properties_neighborhood_id"), table_name="properties")
    op.drop_index(op.f("ix_properties_kitchen_id"), table_name="properties")
    op.drop_index(op.f("ix_properties_heating_id"), table_name="properties")
    op.drop_index(op.f("ix_properties_city_id"), table_name="properties")
    op.drop_table("properties")
    op.drop_index(op.f("ix_neighborhoods_city_id"), table_name="neighborhoods")
    op.drop_table("neighborhoods")
    op.drop_table("transaction_types")
    op.drop_table("sources")
    op.drop_table("property_types")
    op.drop_table("kitchen_types")
    op.drop_table("heating_types")
    op.drop_table("cities")
