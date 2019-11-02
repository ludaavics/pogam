import re

import sqlalchemy as sa
from sqlalchemy.ext.declarative import declared_attr

from . import Base


class Property(Base):
    """
    A real estate property.

    Attributes:
        id: primary key
        type_id: foreign key to the type of property (Apartment, House, Parking, etc.)
        size: property size, in square meters.
        floor: floor number, starting at 0 for the ground floor.
        floors: number of floors, e.g. for houses or duplex.
        rooms: number of rooms.
        bedrooms: number of bedrooms.
        balconies: number of balconies.
        heating_id: foreign key to the type of heating system (gas, electric, etc.)
        kitchen_id: foreign key to the type of kitchen (separated, opened, etc.)
        dpe_consumption_rating: French "Diagnostique de Performance Energétique" rating
            of energy efficiency. France only.
        dpe_emissions_rating: French "Diagnostique de Performance Energétique" rating
            of greenhouse gas emissions.
        postal_code: postal or ZIP code.
        city_id: foreign key to the property's city.
        neighborhood_id: foreign key to the property's neighborhood.
        latitude: property's latitude.
        longitude: property's longitude.
        north_east_lat: latitude of the north-east corner of a property-boundig box.
        north_east_long: longitude of the north-east corner of a property-boundig box.
        south_west_lat: latitude of the south-west corner of a property-boundig box.
        south_east_long: longitude of the south-east corner of a property-boundig box.
    """

    __tablename__ = "properties"
    id: int = sa.Column(sa.Integer, primary_key=True)
    type_id: int = sa.Column(
        sa.Integer,
        sa.ForeignKey("property_types.id", onupdate="CASCADE", ondelete="CASCADE"),
        index=True,
    )
    size: float = sa.Column(sa.Float)
    floor: int = sa.Column(sa.Integer)
    floors: int = sa.Column(sa.Integer, default=1)
    rooms: float = sa.Column(sa.Float)
    bedrooms: float = sa.Column(sa.Float)
    bathrooms: float = sa.Column(sa.Float)
    balconies: int = sa.Column(sa.Integer)
    heating_id: int = sa.Column(
        sa.Integer,
        sa.ForeignKey("heating_types.id", onupdate="CASCADE", ondelete="CASCADE"),
        index=True,
    )
    kitchen_id: int = sa.Column(
        sa.Integer,
        sa.ForeignKey("kitchen_types.id", onupdate="CASCADE", ondelete="CASCADE"),
        index=True,
    )
    dpe_consumption_rating: float = sa.Column(sa.Integer)
    dpe_emissions_rating: float = sa.Column(sa.Integer)
    postal_code: int = sa.Column(sa.Integer)
    city_id: int = sa.Column(
        sa.Integer,
        sa.ForeignKey("cities.id", onupdate="CASCADE", ondelete="CASCADE"),
        index=True,
    )
    neighborhood_id: int = sa.Column(
        sa.Integer,
        sa.ForeignKey("neighborhoods.id", onupdate="CASCADE", ondelete="CASCADE"),
        index=True,
    )
    latitude: float = sa.Column(sa.Float)
    longitude: float = sa.Column(sa.Float)
    north_east_lat: float = sa.Column(sa.Float)
    north_east_long: float = sa.Column(sa.Float)
    south_west_lat: float = sa.Column(sa.Float)
    south_west_long: float = sa.Column(sa.Float)
    map_poly: str = sa.Column(sa.Unicode(10_000))

    type_ = sa.orm.relationship("PropertyType")
    listings = sa.orm.relationship("Listing", back_populates="property")


class Listing(Base):
    """
    The listing for a real estate property.

    Attributes:
    """

    __tablename__ = "listings"
    id: int = sa.Column(sa.Integer, primary_key=True)
    property_id: int = sa.Column(
        sa.Integer,
        sa.ForeignKey("properties.id", onupdate="CASCADE", ondelete="CASCADE"),
        index=True,
    )
    transaction_id: int = sa.Column(
        sa.Integer,
        sa.ForeignKey("transaction_types.id", onupdate="CASCADE", ondelete="CASCADE"),
    )
    description: str = sa.Column(sa.Unicode(1_000_000))
    price: float = sa.Column(sa.Float)
    external_listing_id: str = sa.Column(sa.Unicode(50))

    property = sa.orm.relationship("Property", back_populates="listings")
    type_ = sa.orm.relationship("TransactionType")


class QuasiEnumMixin(object):
    """
    Abstract class for Enum-like tables: a few rows listing mutually exclusive options.
    """

    @declared_attr
    def __tablename__(cls):
        s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", cls.__name__)
        return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower() + "s"

    id: int = sa.Column(sa.Integer, primary_key=True)
    name: str = sa.Column(sa.Unicode(20))


class PropertyType(QuasiEnumMixin, Base):
    pass


class TransactionType(QuasiEnumMixin, Base):
    pass


class HeatingType(QuasiEnumMixin, Base):
    pass


class KitchenType(QuasiEnumMixin, Base):
    pass


class City(QuasiEnumMixin, Base):

    __tablename__ = "cities"


class Neighborhood(QuasiEnumMixin, Base):

    city_id: int = sa.Column(
        sa.Integer,
        sa.ForeignKey("cities.id", onupdate="CASCADE", ondelete="CASCADE"),
        index=True,
    )
