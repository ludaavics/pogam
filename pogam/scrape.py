import re
from enum import Enum
from typing import Dict, Tuple, Union, Iterable

import requests
from fake_useragent import UserAgent  # type: ignore

from . import db
from .models import Listing, Property


class Transaction(Enum):
    rent = 1
    buy = 2


class PropertyType(Enum):
    apartment = 1
    house = 2
    parking = 3
    land = 4
    store = 6
    business = 7
    office = 8
    loft = 9
    apartment_building = 11
    other_building = 12
    castle = 13
    mansion = 14
    program = 15


Transactions = Union[Transaction, Iterable[Transaction]]
PropertyTypes = Union[PropertyType, Iterable[PropertyType]]


def seloger(
    transactions: Transactions,
    post_codes: Union[str, Iterable[str]],
    property_types: Iterable[PropertyType] = ["apartment", "house"],
    min_price: float = None,
    max_price: float = None,
    min_size: float = None,
    max_size: float = None,
    min_rooms: float = None,
    max_rooms: float = None,
    min_bedrooms: float = None,
    max_bedrooms: float = None,
    headers: Dict[str, str] = None,
):
    if isinstance(transactions, Transaction) or isinstance(transactions, str):
        transactions = [transactions]
    transactions = [t.lower() for t in transactions]
    for transaction in transactions:
        if transaction not in Transaction._member_names_:
            msg = (
                f"Unknown transaction '{transaction}'. Expected one of "
                f"{', '.join(Transaction._member_names_)}"
            )
            raise ValueError(msg)
    transactions = [Transaction[transaction].value for transaction in transactions]

    if isinstance(post_codes, str):
        post_codes = [post_codes]

    if isinstance(property_types, str):
        property_types = [property_types]
    property_types = [p.lower() for p in property_types]
    for property_type in property_types:
        if property_type not in PropertyType._member_names_:
            msg = (
                f"Unknown property_type '{property_type}'. Expected one of "
                f"{', '.join(PropertyType._member_names_)}"
            )
            raise ValueError(msg)
    property_types = [
        PropertyType[property_type].value for property_type in property_types
    ]

    search_url = "https://www.seloger.com/list.html"
    max_rooms = max_rooms + 1 if max_rooms is not None else 10
    max_bedrooms = min(
        max_bedrooms + 1 if max_bedrooms is not None else 10, max_rooms - 1
    )
    params = {
        "projects": transactions,
        "types": property_types,
        "natures": [1, 2],  # ancien, neuf. we exclude viager, project de construction
        "cp": post_codes,
        "price": f"{min_price or 0}/{max_price or 'NaN'}",
        "surface": f"{min_size or 0}/{max_size or 'NaN'}",
        "rooms": list(range(min_rooms or 0, max_rooms)),
        "bedrooms": list(range(min_bedrooms or 0, max_bedrooms)),
    }

    if headers is None:
        ua = UserAgent()
        headers = {"user-agent": ua.random}
    page = requests.get(search_url, headers=headers, params=params)


def _seloger(url: str, headers: Dict[str, str] = None) -> Tuple[Property, Listing]:
    """
    Scrape a single listing from seloger.com.

    Args:
        url: URL of the listing.
        headers: headers to be included in the request (e.g. User-Agent)

    Returns:
        a property and a listing instance.
    """
    if headers is None:
        ua = UserAgent()
        headers = {"user-agent": ua.random}
    page = requests.get(url, headers=headers)

    is_field = (
        r"Object\.defineProperty\(\s*ConfigDetail,\s*['\"](.*)['\"],\s*"
        r"{\s*value:\s*['\"](.*)['\"],\s*enumerable:\s*\S+\s*}"
    )
    matches = dict(re.findall(is_field, page.text))

    fields = {
        "property_type": "typeBien",
        "size": "surfaceT",
        "floor": "etage",
        "rooms": "nbPieces",
        "bedrooms": "nbChambres",
        "balconies": "balcon",
        "heating": "idTypeChauffage",
        "kitchen": "idTypeCuisine",
        "dpe_consumption": "dpeC",
        "dpe_emissions": "dpeL",
        "postal_code": "cp",
        "city": "ville",
        "neighborhood": "nomQuartier",
        "latitude": "mapCoordonneesLatitude",
        "longitude": "mapCoordonneesLongitude",
        "north_east_lat": "mapBoundingboxNortheastLatitude",
        "north_east_long": "mapBoundingboxNortheastLongitude",
        "south_west_lat": "mapBoundingboxSouthwestLatitude",
        "south_west_long": "mapBoundingboxSouthwestLongitude",
        "transaction": "typeTransaction",
        "description": "descriptionBien",
        "price": "rawPrice",
        "external_listing_id": "idAnnonce",
    }

    data = {field: matches.get(fields[field], None) for field in fields}
    data["bathrooms"] = (
        float(matches.get("bain", 0) or 0) + float(matches.get("eau", 0) or 0) / 2
    )

    # replace the french decimal comma with the decimal point on numerical fields
    for field in [
        "size",
        "floor",
        "floors",
        "rooms",
        "bedrooms",
        "balconies",
        "dpe_consumption",
        "dpe_emissions",
        "latitude",
        "longitude",
        "north_east_lat",
        "north_east_long",
        "south_west_lat",
        "south_west_long",
    ]:
        try:
            data[field] = data[field].replace(",", ".")
        except (KeyError, ValueError):
            pass

    property = Property.create(data)
    db.session.add(property)
    db.session.flush()
    data.update({"property_id": property.id})
    listing = Listing.create(data)
    db.session.add(listing)
    db.session.commit()

    return property, listing
