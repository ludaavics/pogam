import itertools as it
import logging
import os
import random
import re
from enum import Enum
from math import ceil, floor
from typing import Dict, Iterable, List, Optional, Tuple, Union, cast
from urllib.parse import unquote, urljoin, urlparse

import requests
from bs4 import BeautifulSoup  # type: ignore
from fake_useragent import UserAgent  # type: ignore

from ..models import Listing, Property, Source

logger = logging.getLogger(__name__)


class Captcha(requests.exceptions.RequestException):
    pass


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
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    min_size: Optional[float] = None,
    max_size: Optional[float] = None,
    min_rooms: Optional[float] = None,
    max_rooms: Optional[float] = None,
    min_beds: Optional[float] = None,
    max_beds: Optional[float] = None,
    num_results: int = 100,
    max_duplicates: int = 25,
) -> Dict[str, Union[List[str], List[Listing]]]:
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
        min_beds: minimum number of bedrooms.
        max_beds: maximum number of bedrooms.
        num_results: keep scraping until we add this many result to the database.
        max_duplicates: keep scraping until we see this many consecutive listings
            that are already in our database.

    Returns:
        a dictionary of "added", "seen" and "failed" listings.
    """
    # TO DO: other criteria
    # parking=1,lastfloor=1,hearth=1,guardian=1,view=1,balcony=1/1,pool=1,terrace=1,
    # cellar=1,south=1,box=1,parquet=1,locker=1,disabledaccess=1,alarm=1,toilet=1,
    # bathtub=1/1,shower=1/1,hall=1,livingroom=1,diningroom=1,kitchen=5,heating=8192,
    # unobscured=1,picture=15,exclusiveness=1,pricechange=1,privateseller=1,
    # video=1,vv=1,enterprise=0,garden=1,basement=1
    from .. import db

    allowed_transactions = cast(Iterable[str], Transaction._member_names_)
    if transaction not in allowed_transactions:
        msg = (
            f"Unknown transaction '{transaction}'. Expected one of "
            f"{', '.join(allowed_transactions)}"
        )
        raise ValueError(msg)
    transaction = cast(str, Transaction[transaction].value)

    if isinstance(post_codes, str):
        post_codes = [post_codes]

    if isinstance(property_types, str):
        property_types = [property_types]
    property_types = [p.lower() for p in property_types]
    allowed_property_types = cast(Iterable[str], PropertyType._member_names_)
    for property_type in property_types:
        if property_type not in allowed_property_types:
            msg = (
                f"Unknown property_type '{property_type}'. Expected one of "
                f"{', '.join(allowed_property_types)}"
            )
            raise ValueError(msg)
    property_types = [
        PropertyType[property_type].value for property_type in property_types
    ]

    # we cast to int's here instead of requesting in the signature because scrapers
    # of other sources may accept floats.
    min_price = floor(min_price) if min_price is not None else min_price
    max_price = ceil(max_price) if max_price is not None else max_price
    min_size = floor(min_size) if min_size is not None else min_size
    max_size = ceil(max_size) if max_size is not None else max_size
    min_rooms = floor(min_rooms) if min_rooms is not None else min_rooms
    max_rooms = ceil(max_rooms) if max_rooms is not None else max_rooms
    min_beds = floor(min_beds) if min_beds is not None else min_beds
    max_beds = ceil(max_beds) if max_beds is not None else max_beds

    # fetch all the listings already processed
    already_done_listings = (
        db.session.query(Listing).join(Source).filter(Source.name == "seloger").all()
    )
    already_done_external_ids = [
        listing.external_listing_id for listing in already_done_listings
    ]

    # build the search url
    search_url = "https://www.seloger.com/list.html"
    max_rooms = max_rooms + 1 if max_rooms is not None else 10
    max_beds = min(max_beds + 1 if max_beds is not None else 10, max_rooms - 1)
    params: Dict[str, Union[float, str]] = {
        "projects": transaction,
        "types": ",".join(map(str, property_types)),
        "places": "[" + "|".join([f"{{cp:{pc}}}" for pc in post_codes]) + "]",
        "price": f"{min_price or 0}/{max_price or 'NaN'}",
        "surface": f"{min_size or 0}/{max_size or 'NaN'}",
        "rooms": ",".join(map(str, range(min_rooms or 0, max_rooms))),
        "bedrooms": ",".join(map(str, range(min_beds or 0, max_beds))),
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

    added_listings: List[Listing] = []
    seen_listings: List[Listing] = []
    failed_listings: List[str] = []
    scraped = 0
    consecutive_duplicates = 0
    page_num = 0
    while (scraped < num_results) and (consecutive_duplicates < max_duplicates):

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
            except requests.exceptions.RequestException:
                search_attempts += 1
                continue
            if "captcha" in urlparse(page.url).path:
                search_attempts += 1
                continue
            break
        soup = BeautifulSoup(page.text, "html.parser")

        is_seloger = r".*seloger.com.*"  # exclude sponsored external listings
        links = [
            link["href"]
            for link in soup.find_all(
                "a", attrs={"name": "classified-link", "href": re.compile(is_seloger)}
            )
        ]
        links = [urljoin(link, urlparse(link).path) for link in links]
        if not links:
            break

        # scrape each of the listings on the page
        total = len(links)
        done = [False for _ in range(total)]
        msg = (
            f"Starting the scrape of {total} listings "
            f"fetched from {unquote(page.url)} ."
        )
        logger.info(msg)
        previous_round = -1
        while sum(done) > previous_round:
            previous_round = sum(done)
            for i, link in enumerate(links):
                if done[i]:
                    continue

                seloger_id = os.path.basename(urlparse(link).path).split(".")[0]
                if seloger_id in already_done_external_ids:
                    msg = f"Skipping link #{i}, as it is already in our DB: {link}."
                    logger.debug(msg)
                    done[i] = True
                    consecutive_duplicates += 1
                    seen_listings.append(
                        already_done_listings[
                            already_done_external_ids.index(seloger_id)
                        ]
                    )
                    continue

                msg = f"Scraping link #{i}: {link} ..."
                logger.debug(msg)
                proxy = next(proxy_pool)
                proxies = {"http": proxy, "https": proxy}
                try:
                    listing, is_new = _seloger(
                        link, headers={"User-Agent": ua.random}, proxies=proxies
                    )
                except requests.exceptions.RequestException:
                    msg = f"👻Failed to retrieve the page.👻"
                    logger.debug(msg)
                    continue
                except Exception:
                    # we don't want to interrupt the program, but we don't want to
                    # silence the unexpected error.
                    msg = f"💥Unpexpected error.💥"
                    logging.exception(msg)
                    continue
                msg = f"💫Scrape suceeded.💫"
                logger.debug(msg)
                done[i] = True
                if is_new:
                    consecutive_duplicates = 0
                    added_listings.append(listing)
                else:
                    consecutive_duplicates += 1
                    seen_listings.append(listing)
                if consecutive_duplicates >= max_duplicates:
                    break

        failed_listings += [link for is_done, links in zip(done, links) if not is_done]
        scraped += sum(done)
        page_num += 1

    return {"added": added_listings, "seen": seen_listings, "failed": failed_listings}


def _seloger(
    url: str, headers: Dict[str, str] = None, proxies=None, timeout=5
) -> Tuple[Listing, bool]:
    """
    Scrape a single listing from seloger.com.

    Args:
        url: URL of the listing.
        headers: headers to be included in the request (e.g. User-Agent)

    Returns:
        an instance of the scraped listing and a flag indicating whether it is a new
        listing.
    """
    from .. import db

    if headers is None:
        ua = UserAgent()
        headers = {"user-agent": ua.random}
    page = requests.get(url, headers=headers, proxies=proxies, timeout=timeout)
    if "captcha" in page.url:
        raise Captcha

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
            data[field] = float(data[field].replace(",", "."))
        except (KeyError, ValueError, AttributeError):
            pass

    data["source"] = "seloger"
    data["url"] = url

    property = Property.create(data)
    db.session.add(property)
    db.session.flush()
    data.update({"property_id": property.id})
    listing, is_new = Listing.get_or_create(**data)
    if is_new:
        db.session.add(listing)
        db.session.commit()

    return listing, is_new
