import re

import sqlalchemy as sa
from sqlalchemy.ext.declarative import declared_attr

from . import db


DPE_CONSUMPTION = {"A": 50, "B": 70, "C": 120, "D": 190, "E": 280, "F": 390, "G": 450}
DPE_EMISSIONS = {"A": 5, "B": 7.5, "C": 15, "D": 27.5, "E": 45, "F": 67.5}
ROSETTA_STONE = {"appartement": "apartment"}


class Property(db.Model):
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
        dpe_consumption: French "Diagnostique de Performance Energétique" rating
            of energy efficiency.
        dpe_emissions: French "Diagnostique de Performance Energétique" rating
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
    dpe_consumption: float = sa.Column(sa.Integer)
    dpe_emissions: float = sa.Column(sa.Integer)
    postal_code: int = sa.Column(sa.Integer)
    city_id: int = sa.Column(
        sa.Integer,
        sa.ForeignKey("cities.id", onupdate="CASCADE", ondelete="RESTRICT"),
        index=True,
    )
    neighborhood_id: int = sa.Column(
        sa.Integer,
        sa.ForeignKey("neighborhoods.id", onupdate="CASCADE", ondelete="RESTRICT"),
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

    @staticmethod
    def create(data):
        """
        Create a new Property.
        """
        property_type = PropertyType.get_or_create(data.get("property_type", None))
        if property_type is not None:
            db.session.add(property_type)
            db.session.flush()
            data.update({"type_id": property_type.id})

        heating = HeatingType.get_or_create(data.get("heating", None))
        if heating is not None:
            db.session.add(heating)
            db.session.flush()
            data.update({"heating_id": heating.id})

        kitchen = KitchenType.get_or_create(data.get("kitchen", None))
        if kitchen is not None:
            db.session.add(kitchen)
            db.session.flush()
            data.update({"kitchen_id": kitchen.id})

        city = City.get_or_create(data.get("city", None))
        if city is not None:
            db.session.add(city)
            db.session.flush()
            data.update({"city_id": city.id})

        neighborhood = Neighborhood.get_or_create(data.get("neighborhood", None))
        if neighborhood is not None:
            db.session.add(neighborhood)
            db.session.flush()
            data.update({"neighborhood_id": neighborhood.id})

        # convert letter ratings into number ratings
        for rating_name in ["dpe_consumption", "dpe_emissions"]:
            rating_value = data.get(rating_name, None)
            if isinstance(rating_value, str) and rating_value.isalpha():
                rating_value = globals()[rating_name.upper()].get(
                    rating_value.upper(), ""
                )
                data.update({rating_name: rating_value})

        data = {k: data[k] for k in data if hasattr(Property, k)}
        data = {k: (data[k] if data[k] else None) for k in data}

        property = Property(**data)
        return property


class Listing(db.Model):
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
    mortgage: float = sa.Column(sa.Float)
    external_listing_id: str = sa.Column(sa.Unicode(50))

    property = sa.orm.relationship("Property", back_populates="listings")
    type_ = sa.orm.relationship("TransactionType")

    @staticmethod
    def create(data):
        """Create a new listing."""
        data = {k: data[k] for k in data if hasattr(Listing, k)}
        listing = Listing(**data)
        return listing


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

    @declared_attr
    def __table_args__(cls):
        return (sa.UniqueConstraint("name"),)

    @classmethod
    def create(cls, name):
        return cls(name=name)

    @classmethod
    def get_or_create(cls, name, **kwargs):
        if name is None:
            return None
        name = name.lower()
        name = ROSETTA_STONE.get(name, name)
        try:
            return cls.query.filter_by(name=name).one()
        except sa.orm.exc.NoResultFound:
            return cls.create(name, **kwargs)


class PropertyType(QuasiEnumMixin, db.Model):
    pass


class TransactionType(QuasiEnumMixin, db.Model):
    pass


class HeatingType(QuasiEnumMixin, db.Model):
    pass


class KitchenType(QuasiEnumMixin, db.Model):
    pass


class City(QuasiEnumMixin, db.Model):

    __tablename__ = "cities"


class Neighborhood(QuasiEnumMixin, db.Model):

    city_id: int = sa.Column(
        sa.Integer,
        sa.ForeignKey("cities.id", onupdate="CASCADE", ondelete="CASCADE"),
        index=True,
    )
