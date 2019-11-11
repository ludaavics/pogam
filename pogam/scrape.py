import itertools as it
import logging
import random
import re
from enum import Enum
from typing import Dict, Iterable, Tuple, Union
from urllib.parse import unquote, urljoin, urlparse

import requests
from bs4 import BeautifulSoup  # type: ignore
from fake_useragent import UserAgent  # type: ignore

from . import db
from .models import Listing, Property

logger = logging.getLogger(__name__)


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


def seloger(
    transaction: str,
    post_codes: Union[str, Iterable[str]],
    property_types: Union[str, Iterable[str]] = ["apartment", "house"],
    min_price: float = None,
    max_price: float = None,
    min_size: float = None,
    max_size: float = None,
    min_rooms: float = None,
    max_rooms: float = None,
    min_bedrooms: float = None,
    max_bedrooms: float = None,
    num_results: int = 100,
    max_duplicates: int = 25,
):
    """
    Scrape all listing matching search criteria.

    Args:
        transaction: one of {'rent', 'buy'}
        post_codes: list of post codes.
        property_types: subest of {'apartment', 'house', 'parking',
            'land', 'store', 'business', 'office', 'loft',
            'apartment_building', 'other_building', 'castle',
            'mansion', 'program'}.
        min_price: minimum requested price.
        max_price: maximum requested price.
        min_size: minimum property size, in square meters.
        max_size: maximum property size, in square meters.
        min_rooms: minimum number of rooms.
        max_rooms: maximum number of rooms.
        min_bedrooms: minimum number of bedrooms.
        max_bedrooms: maximum number of bedrooms.
        num_results: approximate number of listings to scrape.

    Returns:
        TO DO
    """
    allowed_transactions: Iterable[str] = Transaction._member_names_
    if transaction not in allowed_transactions:
        msg = (
            f"Unknown transaction '{transaction}'. Expected one of "
            f"{', '.join(Transaction._member_names_)}"
        )
        raise ValueError(msg)
    transaction = Transaction[transaction].value

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

    # build the search url
    search_url = "https://www.seloger.com/list.html"
    max_rooms = max_rooms + 1 if max_rooms is not None else 10
    max_bedrooms = min(
        max_bedrooms + 1 if max_bedrooms is not None else 10, max_rooms - 1
    )
    params = {
        "projects": transaction,
        "types": ",".join(map(str, property_types)),
        "places": "[" + "|".join([f"{{cp:{pc}}}" for pc in post_codes]) + "]",
        "price": f"{min_price or 0}/{max_price or 'NaN'}",
        "surface": f"{min_size or 0}/{max_size or 'NaN'}",
        "rooms": ",".join(map(str, range(min_rooms or 0, max_rooms))),
        "bedrooms": ",".join(map(str, range(min_bedrooms or 0, max_bedrooms))),
        "enterprise": 0,
        "qsVersion": 1.0,
    }
    if transaction == Transaction.buy.value:
        params.update(
            {"natures": "1,2"}
        )  # ancien, neuf. we exclude viager, project de construction

    # generate user agent
    ua = UserAgent()
    headers = {"user-agent": ua.random}

    # get a list of proxies
    proxy_list = requests.get(
        "https://www.proxy-list.download/api/v1/get", params={"type": "https"}
    ).text.split()
    random.shuffle(proxy_list)
    proxy_pool = it.cycle(proxy_list)

    failed = []
    scraped = 0
    already_seen = 0
    page_num = 0
    while (scraped < num_results) and (already_seen < max_duplicates):

        # get a page of results
        if page_num != 0:
            params.update({"LISTING-LISTpg": page_num + 1})
        search_attempts = 0
        while search_attempts < len(proxy_list):
            proxy = next(proxy_pool)
            proxies = {"http": proxy, "https": proxy}
            try:
                page = requests.get(
                    search_url,
                    headers=headers,
                    params=params,
                    proxies=proxies,
                    timeout=5,
                )
            except (
                requests.exceptions.ProxyError,
                requests.exceptions.ConnectionError,
            ):
                search_attempts += 1
                continue
            break
        soup = BeautifulSoup(page.text, "html.parser")

        is_seloger = r".*seloger.com/annonces/.*"  # exclude sponsored external listings
        links = [
            link["href"]
            for link in soup.find_all(
                "a", attrs={"name": "classified-link", "href": re.compile(is_seloger)}
            )
        ]
        if not links:
            break

        # scrape each of the listings on the page
        total = len(links)
        done = [False for _ in range(total)]
        msg = (
            f"Starting the scrape of {total} listings fetched from {unquote(page.url)}."
        )
        logger.info(msg)
        previous_round = -1
        while sum(done) > previous_round:
            previous_round = sum(done)
            for i, link in enumerate(links):
                if done[i]:
                    continue
                url = urljoin(link, urlparse(link).path)
                proxy = next(proxy_pool)
                proxies = {"http": proxy, "https": proxy}

                try:
                    _, is_new = _seloger(
                        url, headers={"User-Agent": ua.random}, proxies=proxies
                    )
                except Exception as e:
                    logger.debug(e)
                    continue
                done[i] = True
                already_seen = 0 if is_new else already_seen + 1

        failed += [link for is_done, links in zip(done, links) if not is_done]
        scraped += sum(done)
        page_num += 1

    return failed


def _seloger(
    url: str, headers: Dict[str, str] = None, proxies=None, timeout=5
) -> Tuple[Property, Listing]:
    """
    Scrape a single listing from seloger.com.

    Args:
        url: URL of the listing.
        headers: headers to be included in the request (e.g. User-Agent)

    Returns:
        a property and a listing instance.
    """
    msg = f"Scraping {url} ..."
    logger.debug(msg)
    if headers is None:
        ua = UserAgent()
        headers = {"user-agent": ua.random}
    page = requests.get(url, headers=headers, proxies=proxies, timeout=timeout)

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
        except (KeyError, ValueError, AttributeError):
            pass

    property = Property.create(data)
    db.session.add(property)
    db.session.flush()
    data.update({"property_id": property.id})
    listing, is_new = Listing.get_or_create(data)
    if is_new:
        db.session.add(listing)
        db.session.commit()

    return listing, is_new
