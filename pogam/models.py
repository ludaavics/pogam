import re
from typing import Dict, List

import sqlalchemy as sa  # type: ignore
from sqlalchemy.ext.declarative import declared_attr  # type: ignore

from . import db

DPE_CONSUMPTION = {"A": 50, "B": 70, "C": 120, "D": 190, "E": 280, "F": 390, "G": 450}
DPE_EMISSIONS = {"A": 5, "B": 7.5, "C": 15, "D": 27.5, "E": 45, "F": 67.5}
ROSETTA_STONE = {"appartement": "apartment", "location": "rent"}


__all__ = [
    "Property",
    "Listing",
    "Source",
    "PropertyType",
    "TransactionType",
    "Heating",
    "Kitchen",
    "City",
    "Neighborhood",
]


class TimestampMixin(object):
    created_at = sa.Column(sa.DateTime, default=sa.func.now())


class UniqueMixin(object):
    @classmethod
    def unique_columns(cls):
        raise NotImplementedError

    @classmethod
    def create(cls, **data):
        return cls(**data)

    @classmethod
    def get_or_create(cls, **data):
        unique_columns = {k: data.get(k, None) for k in cls.unique_columns()}

        try:
            obj = cls.query.filter_by(**unique_columns).one()
            is_new = False
        except sa.orm.exc.NoResultFound:
            with db.session.no_autoflush:
                obj = cls.create(**data)
                is_new = True
                db.session.add(obj)
        return obj, is_new


class QuasiEnumMixin(UniqueMixin):
    """
    Abstract class for Enum-like tables: a few rows listing mutually exclusive options.
    """

    @declared_attr
    def __tablename__(cls):
        s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", cls.__name__)
        return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower() + "s"

    id: int = sa.Column(sa.Integer, primary_key=True)
    name: str = sa.Column(sa.Unicode(100))

    @declared_attr
    def __table_args__(cls):
        return (sa.UniqueConstraint("name"),)

    @classmethod
    def unique_columns(cls):
        return ["name"]

    @classmethod
    def get_or_create(cls, name):
        if name is None:
            return None, None
        name = name.lower()
        name = ROSETTA_STONE.get(name, name)
        return super().get_or_create(name=name)


class PropertyType(QuasiEnumMixin, db.Model):
    pass


class Source(QuasiEnumMixin, db.Model):
    pass


class TransactionType(QuasiEnumMixin, db.Model):
    pass


class Heating(QuasiEnumMixin, db.Model):
    pass


class Kitchen(QuasiEnumMixin, db.Model):
    pass


class City(QuasiEnumMixin, db.Model):

    __tablename__ = "cities"


class Neighborhood(QuasiEnumMixin, db.Model):

    city_id: int = sa.Column(
        sa.Integer,
        sa.ForeignKey("cities.id", onupdate="CASCADE", ondelete="CASCADE"),
        index=True,
    )


class Property(TimestampMixin, db.Model):
    """
    A real estate property.

    Attributes:
        id: primary key
        type_: type of property (Apartment, House, Parking, etc.)
        size: property size, in square meters.
        floor: floor number, starting at 0 for the ground floor.
        floors: number of floors, e.g. for houses or duplex.
        rooms: number of rooms.
        bedrooms: number of bedrooms.
        bathrooms: number of bathrooms.
        balconies: number of balconies.
        heating: type of heating system (gas, electric, etc.)
        kitchen: type of kitchen (separated, opened, etc.)
        dpe_consumption: French "Diagnostique de Performance Energétique" rating
            of energy efficiency.
        dpe_emissions: French "Diagnostique de Performance Energétique" rating
            of greenhouse gas emissions.
        postal_code: postal or ZIP code.
        city: the property's city.
        neighborhood: he property's neighborhood, within the city.
        latitude: property's latitude.
        longitude: property's longitude.
        north_east_lat: latitude of the north-east corner of a property-boundig box.
        north_east_long: longitude of the north-east corner of a property-boundig box.
        south_west_lat: latitude of the south-west corner of a property-boundig box.
        south_east_long: longitude of the south-east corner of a property-boundig box.
    """

    __tablename__ = "properties"

    # what
    id: int = sa.Column(sa.Integer, primary_key=True)
    type_id: int = sa.Column(
        sa.Integer,
        sa.ForeignKey("property_types.id", onupdate="CASCADE", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )
    type_: PropertyType = sa.orm.relationship("PropertyType")
    size: float = sa.Column(sa.Float)
    floor: int = sa.Column(sa.Integer)
    floors: int = sa.Column(sa.Integer, default=1)
    rooms: float = sa.Column(sa.Float)
    bedrooms: float = sa.Column(sa.Float)
    bathrooms: float = sa.Column(sa.Float)
    balconies: int = sa.Column(sa.Integer)
    terraces: int = sa.Column(sa.Integer)
    heating_id: int = sa.Column(
        sa.Integer,
        sa.ForeignKey("heatings.id", onupdate="CASCADE", ondelete="RESTRICT"),
        index=True,
    )
    heating: Heating = sa.orm.relationship("Heating")
    kitchen_id: int = sa.Column(
        sa.Integer,
        sa.ForeignKey("kitchens.id", onupdate="CASCADE", ondelete="RESTRICT"),
        index=True,
    )
    kitchen: Kitchen = sa.orm.relationship("Kitchen")
    has_lawn: bool = sa.Column(sa.Boolean(create_constraint=False))
    has_pool: bool = sa.Column(sa.Boolean(create_constraint=False))
    has_elevator: bool = sa.Column(sa.Boolean(create_constraint=False))
    has_fireplace: bool = sa.Column(sa.Boolean(create_constraint=False))
    has_hardwood_floors: bool = sa.Column(sa.Boolean(create_constraint=False))
    has_view: bool = sa.Column(sa.Boolean(create_constraint=False))
    exposure: str = sa.Column(sa.Unicode(50))
    has_cellar: bool = sa.Column(sa.Boolean(create_constraint=False))
    parkings: int = sa.Column(sa.Integer)
    has_super: bool = sa.Column(sa.Boolean(create_constraint=False))
    dpe_consumption: float = sa.Column(sa.Integer)
    dpe_emissions: float = sa.Column(sa.Integer)

    # where
    postal_code: str = sa.Column(sa.Unicode(50))
    city_id: int = sa.Column(
        sa.Integer,
        sa.ForeignKey("cities.id", onupdate="CASCADE", ondelete="RESTRICT"),
        index=True,
    )
    city: City = sa.orm.relationship("City")
    neighborhood_id: int = sa.Column(
        sa.Integer,
        sa.ForeignKey("neighborhoods.id", onupdate="CASCADE", ondelete="RESTRICT"),
        index=True,
    )
    neighborhood: Neighborhood = sa.orm.relationship("Neighborhood")
    latitude: float = sa.Column(sa.Float)
    longitude: float = sa.Column(sa.Float)
    north_east_lat: float = sa.Column(sa.Float)
    north_east_long: float = sa.Column(sa.Float)
    south_west_lat: float = sa.Column(sa.Float)
    south_west_long: float = sa.Column(sa.Float)
    map_poly: str = sa.Column(sa.Unicode(100_000))

    listings: List["Listing"] = sa.orm.relationship(
        "Listing", back_populates="property_"
    )

    @staticmethod
    def create(data: Dict) -> "Property":
        """
        Create a new Property.

        Arguments:
            data: dictionary of values for the property's fields.
        """
        _property_type = data.get("property_type", None)
        if _property_type is None:
            msg = "Field 'property_type' is required."
            raise ValueError(msg)
        property_type, is_new = PropertyType.get_or_create(_property_type)
        db.session.flush()
        data.update({"type_id": property_type.id})

        heating, _ = Heating.get_or_create(data.pop("heating", None))
        db.session.flush()
        if heating is not None:
            data.update({"heating_id": heating.id})

        kitchen, _ = Kitchen.get_or_create(data.pop("kitchen", None))
        db.session.flush()
        if kitchen is not None:
            data.update({"kitchen_id": kitchen.id})

        city, _ = City.get_or_create(data.pop("city", None))
        db.session.flush()
        if city is not None:
            data.update({"city_id": city.id})

        neighborhood, _ = Neighborhood.get_or_create(data.pop("neighborhood", None))
        db.session.flush()
        if neighborhood is not None:
            data.update({"neighborhood_id": neighborhood.id})

        # convert letter ratings into number ratings
        for rating_name in ["dpe_consumption", "dpe_emissions"]:
            rating_value = data.get(rating_name, None)
            if isinstance(rating_value, str) and rating_value.isalpha():
                rating_value = globals()[rating_name.upper()].get(
                    rating_value.upper(), ""
                )
                data.update({rating_name: rating_value})

        columns = {k: data[k] for k in data if hasattr(Property, k)}
        # we want to replace all falsy values, except an explicit False, with None
        columns = {
            k: (columns[k] if (columns[k] or (columns[k] is False)) else None)
            for k in columns
        }

        property_ = Property(**columns)
        return property_

    def to_dict(self):
        """Convert the property object to a dictionary."""
        return {
            "id": self.id,
            "type": self.type_.name,
            "size": self.size,
            "floor": self.floor,
            "floors": self.floors,
            "rooms": self.rooms,
            "bedrooms": self.bedrooms,
            "bathrooms": self.bathrooms,
            "balconies": self.balconies,
            "terraces": self.terraces,
            "heating": self.heating.name if self.heating else None,
            "kitchen": self.kitchen.name if self.kitchen else None,
            "has_lawn": self.has_lawn,
            "has_pool": self.has_pool,
            "has_elevator": self.has_elevator,
            "has_fireplace": self.has_fireplace,
            "has_hardwood_floors": self.has_hardwood_floors,
            "has_view": self.has_view,
            "exposure": self.exposure,
            "has_cellar": self.has_cellar,
            "parkings": self.parkings,
            "has_super": self.has_super,
            "dpe_consumption": self.dpe_consumption,
            "dpe_emissions": self.dpe_emissions,
            "postal_code": self.postal_code,
            "city": self.city.name if self.city else None,
            "neighborhood": self.neighborhood.name if self.neighborhood else None,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "north_east_lat": self.north_east_lat,
            "north_east_long": self.north_east_long,
            "south_west_lat": self.south_west_lat,
            "south_west_long": self.south_west_long,
        }


class Listing(TimestampMixin, UniqueMixin, db.Model):
    """
    The listing for a real estate property.

    Attributes:
        id: primary key
        property: reference property.
        source: source of the scrape.
        url: url of the source listing.
        transaction: type of transaction (buy, rent).
        description: full text description in the listing.
        price: listing's price.
        currency: listing's currency.
        external_listing_id: source's listing id
    """

    __tablename__ = "listings"
    id: int = sa.Column(sa.Integer, primary_key=True)
    property_id: int = sa.Column(
        sa.Integer,
        sa.ForeignKey("properties.id", onupdate="CASCADE", ondelete="CASCADE"),
        index=True,
    )
    source_id: int = sa.Column(
        sa.Integer,
        sa.ForeignKey("sources.id", onupdate="CASCADE", ondelete="CASCADE"),
        index=True,
    )
    url: str = sa.Column(sa.Unicode(10_000))
    first_publication_date: str = sa.Column(
        sa.Unicode(100)
    )  # https://github.com/chanzuckerberg/sqlalchemy-aurora-data-api/issues/7
    transaction_id: int = sa.Column(
        sa.Integer,
        sa.ForeignKey("transaction_types.id", onupdate="CASCADE", ondelete="CASCADE"),
        nullable=False,
    )
    description: str = sa.Column(sa.Unicode(10_000_000))
    is_furnished: bool = sa.Column(sa.Boolean(create_constraint=False))
    price: float = sa.Column(sa.Float)
    currency: str = sa.Column(sa.Unicode(10), default="€")
    broker_fee: float = sa.Column(sa.Float)
    broker_fee_is_included: bool = sa.Column(sa.Boolean(create_constraint=False))
    security_deposit: float = sa.Column(sa.Float)
    external_listing_id: str = sa.Column(sa.Unicode(200))

    property_: Property = sa.orm.relationship("Property", back_populates="listings")
    transaction: TransactionType = sa.orm.relationship("TransactionType")
    source: Source = sa.orm.relationship("Source")

    @classmethod
    def unique_columns(cls):
        return ["external_listing_id"]

    @classmethod
    def create(cls, **data):
        """Create a new listing."""
        transaction, _ = TransactionType.get_or_create(data.get("transaction", None))
        source, _ = Source.get_or_create(data.get("source", None))
        columns = {k: data[k] for k in data if hasattr(Listing, k)}
        new = cls(**columns)
        new.transaction = transaction
        new.source = source

        return new

    def to_dict(self):
        return {
            "id": self.id,
            "transaction": self.transaction.name,
            "source": self.source.name,
            "first_publication_date": self.first_publication_date,
            "price": self.price,
            "currency": self.currency,
            "broker_fee": self.broker_fee,
            "broker_fee_is_included": self.broker_fee_is_included,
            "security_deposit": self.security_deposit,
            "is_furnished": self.is_furnished,
            "description": self.description,
            "property": self.property_.to_dict(),
            "url": self.url,
            "external_listing_id": self.external_listing_id,
        }
