import re
from typing import Dict

import requests
from fake_useragent import UserAgent

from . import db
from .models import Listing, Property


def _seloger(url: str, headers: Dict[str, str] = None) -> (Property, Listing):
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
