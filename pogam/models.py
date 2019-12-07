import re

import sqlalchemy as sa  # type: ignore
from sqlalchemy.ext.declarative import declared_attr  # type: ignore

from . import db

DPE_CONSUMPTION = {"A": 50, "B": 70, "C": 120, "D": 190, "E": 280, "F": 390, "G": 450}
DPE_EMISSIONS = {"A": 5, "B": 7.5, "C": 15, "D": 27.5, "E": 45, "F": 67.5}
ROSETTA_STONE = {"appartement": "apartment", "location": "rent"}


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


class Property(TimestampMixin, db.Model):
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
        sa.ForeignKey("property_types.id", onupdate="CASCADE", ondelete="RESTRICT"),
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
        sa.ForeignKey("heating_types.id", onupdate="CASCADE", ondelete="RESTRICT"),
        index=True,
    )
    kitchen_id: int = sa.Column(
        sa.Integer,
        sa.ForeignKey("kitchen_types.id", onupdate="CASCADE", ondelete="RESTRICT"),
        index=True,
    )
    dpe_consumption: float = sa.Column(sa.Integer)
    dpe_emissions: float = sa.Column(sa.Integer)
    postal_code: str = sa.Column(sa.Unicode(50))
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
    map_poly: str = sa.Column(sa.Unicode(100_000))

    type_ = sa.orm.relationship("PropertyType")
    city = sa.orm.relationship("City")
    neighborhood = sa.orm.relationship("Neighborhood")
    heating = sa.orm.relationship("HeatingType")
    kitchen = sa.orm.relationship("KitchenType")
    listings = sa.orm.relationship("Listing", back_populates="property")

    @staticmethod
    def create(data):
        """
        Create a new Property.
        """
        property_type, _ = PropertyType.get_or_create(data.get("property_type", None))
        if property_type is not None:
            data.update({"type_id": property_type.id})

        heating, _ = HeatingType.get_or_create(data.pop("heating", None))
        if heating is not None:
            data.update({"heating_id": heating.id})

        kitchen, _ = KitchenType.get_or_create(data.pop("kitchen", None))
        if kitchen is not None:
            data.update({"kitchen_id": kitchen.id})

        city, _ = City.get_or_create(data.pop("city", None))
        if city is not None:
            data.update({"city_id": city.id})

        neighborhood, _ = Neighborhood.get_or_create(data.pop("neighborhood", None))
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
        columns = {k: (columns[k] if columns[k] else None) for k in columns}

        property = Property(**columns)
        return property

    def to_dict(self):
        return {
            "id": self.id,
            "type": self.type_.name,
            "postal_code": self.postal_code,
            "city": self.city.name,
            "neighborhood": self.neighborhood.name if self.neighborhood else None,
            "size": self.size,
            "floor": self.floor,
            "floors": self.floors,
            "rooms": self.rooms,
            "bedrooms": self.bedrooms,
            "bathrooms": self.bathrooms,
            "balconies": self.balconies,
            "heating": self.heating.name if self.heating else None,
            "kitchen": self.kitchen.name if self.kitchen else None,
            "dpe_consumption": self.dpe_consumption,
            "dpe_emissions": self.dpe_emissions,
        }


class Listing(TimestampMixin, UniqueMixin, db.Model):
    """
    The listing for a real estate property.

    Attributes:
        id: primary key
        property_id: foreign key to the property.
        source_id: foreign key to the source of the scrape.
        url: url of the source listing.
        transaction_id: foreign key to the type of transaction (buy, rent).
        description: full text description in the listing.
        price: listing's price.
        mortgage: estimated mortgage payment.
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
    transaction_id: int = sa.Column(
        sa.Integer,
        sa.ForeignKey("transaction_types.id", onupdate="CASCADE", ondelete="CASCADE"),
    )
    description: str = sa.Column(sa.Unicode(10_000_000))
    price: float = sa.Column(sa.Float)
    mortgage: float = sa.Column(sa.Float)
    external_listing_id: str = sa.Column(sa.Unicode(200))

    property = sa.orm.relationship("Property", back_populates="listings")
    type_ = sa.orm.relationship("TransactionType")

    @classmethod
    def unique_columns(cls):
        return ["external_listing_id"]

    @classmethod
    def create(cls, **data):
        """Create a new listing."""
        transaction_type, _ = TransactionType.get_or_create(
            data.get("transaction", None)
        )
        if transaction_type is not None:
            data.update({"transaction_id": transaction_type.id})

        source, _ = Source.get_or_create(data.get("source", None))
        if source is not None:
            data.update({"source_id": source.id})

        columns = {k: data[k] for k in data if hasattr(Listing, k)}
        return cls(**columns)

    def to_dict(self):
        return {
            "id": self.id,
            "transaction": self.type_.name,
            "price": self.price,
            "description": self.description,
            "url": self.url,
            "property": self.property.to_dict(),
        }


class Source(QuasiEnumMixin, db.Model):
    pass


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
