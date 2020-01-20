import logging
import os
import random
import time
import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple, Union, cast
from urllib.parse import urlparse

import pytz
import requests
from fake_useragent import UserAgent  # type: ignore

from ..models import Listing, Property
from .proxies import proxy11

try:
    import boto3  # type: ignore
    from botocore.exceptions import ClientError  # type: ignore
except ImportError:
    boto3 = None


logger = logging.getLogger(__name__)


class Transaction(Enum):
    rent = 10
    buy = 9


class PropertyType(Enum):
    house = 1
    apartment = 2
    land = 3
    parking = 4
    other = 5


def leboncoin(
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
    timeout: int = 5,
) -> Dict[str, Union[List[str], List[Listing]]]:
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

    # fetch all the listings already processed
    already_done_urls = [
        l[0]
        for l in db.session.query(Listing.url)
        .filter(Listing.source == "leboncoin")
        .all()
    ]

    # build the search payload
    rooms = {}
    if min_rooms is not None:
        rooms.update({"min": min_rooms})
    if max_rooms is not None:
        rooms.update({"max": max_rooms})
    size = {}
    if min_size is not None:
        size.update({"min": min_size})
    if max_size is not None:
        size.update({"max": max_size})
    price = {}
    if min_price is not None:
        price.update({"min": min_price})
    if max_price is not None:
        price.update({"max": max_price})
    payload = {
        "pivot": "0,0,0",  # page cursor
        "limit": 100,  # number of results par page (100 is server-side max)
        "limit_alu": 1,  # 0 to return only statistics, 1 to also return listings
        "filters": {
            "category": {"id": str(transaction)},
            "enums": {
                "ad_type": ["offer"],
                "real_estate_type": [str(pt) for pt in property_types],
            },
            "ranges": {"rooms": rooms, "square": size, "price": price},
            "location": {
                "locations": [
                    {"locationType": "city", "zipcode": post_code}
                    for post_code in post_codes
                ]
            },
        },
        "sort_by": "time",
        "sort_order": "desc",
    }

    # user agent generator
    ua = UserAgent()

    # get a pool of proxies
    api_key = os.getenv("PROXY11_API_KEY")
    try:
        proxy_pool = proxy11(api_key, type_="anonymous")
    except RuntimeError:
        proxy_pool = None
    proxy = next(proxy_pool)

    # post the query
    search_url = "https://api.leboncoin.fr/api/adfinder/v1/search"
    headers = {
        "User-Agent": ua.random,
        "Accept-Encoding": "gzip, deflate",
        "Accept-Language": "en-US,en;q=0.8,fr;q=0.6",
        "Referer": "https://www.leboncoin.fr/recherche",
        "Origin": "https://www.leboncoin.fr",
    }
    done_with_all_pages = False
    added_listings: List[Listing] = []
    seen_listings: List[Listing] = []
    failed_listings: List[str] = []
    while not done_with_all_pages:

        search_attempts = 0
        max_search_attempts = 50
        while search_attempts < max_search_attempts:
            proxies = {"http": proxy, "https": proxy}

            try:
                request = requests.post(
                    search_url,
                    headers=headers,
                    json=payload,
                    proxies=proxies,
                    timeout=timeout,
                )
            except requests.exceptions.RequestException as e:
                msg = f"👻Failed to retrieve {search_url} ({type(e).__name__}).👻"
                logger.debug(msg)
                proxy = next(proxy_pool)
                headers.update({"User-Agent": ua.random})
                search_attempts += 1
                continue
            if (
                ("captcha" in request.text)
                or ("datadome" in request.text)
                or (not request.text)
                or (request.status_code >= 400)
            ):
                msg = f"👻Failed to retrieve {request.url} (Captcha).👻"
                logger.debug(msg)
                proxy = next(proxy_pool)
                headers.update({"User-Agent": ua.random})
                search_attempts += 1
                continue
            break
        response = request.json()

        # parse json
        done = -1
        consecutive_duplicates = 0
        for i, ad in enumerate(response.get("ads", [])):
            done += 1
            url = ad.get("url")
            if url in already_done_urls:
                msg = f"Skipping ad #{i}, as it is already in our DB: {url}."
                logger.debug(msg)
                consecutive_duplicates += 1
                seen_listings.append(url)
                continue

            msg = f"Parsing ad #{i}: {url} ..."
            logger.debug(msg)
            try:
                listing, is_new = _leboncoin(ad, headers, proxies)
            except Exception:
                msg = f"💥Unpexpected error.💥"
                logging.exception(msg)
                failed_listings.append(url)
                continue
            msg = f"💫Scrape suceeded.💫"
            logger.debug(msg)

            if is_new:
                added_listings.append(listing)
                consecutive_duplicates = 0
            else:
                seen_listings.append(listing)
                consecutive_duplicates += 1

        if (
            ("pivot" in response)
            and (consecutive_duplicates <= max_duplicates)
            and (done <= num_results)
        ):
            sleep = random.randint(5, 35)
            msg = f"Sleeping for {sleep} seconds before going to next page."
            logger.debug(msg)
            time.sleep(sleep)
            payload.update({"pivot": response["pivot"]})
            # NB: we keep the same proxy and user agent
        else:
            done_with_all_pages = True

    return {"added": added_listings, "seen": seen_listings, "failed": failed_listings}


def _leboncoin(
    ad: Mapping[str, Any], headers: Mapping[str, str], proxies: Mapping[str, str]
) -> Tuple[Listing, bool]:

    from .. import db

    fields: Dict[str, str] = {
        "external_listing_id": "list_id",
        "first_publication_date": "first_publication_date",
        "description": "body",
        "url": "url",
        "transaction": "category_name",
        "price": "price",
    }
    data: Dict[str, Any] = {field: ad.get(fields[field]) for field in fields}
    assert isinstance(data["price"], list)
    assert len(data["price"]) == 1
    data["price"] = data["price"][0]
    data["external_listing_id"] = str(data["external_listing_id"])
    assert isinstance(data["first_publication_date"], str)
    data["first_publication_date"] = (
        pytz.timezone("Europe/Paris")
        .localize(datetime.fromisoformat(data["first_publication_date"]))
        .astimezone(pytz.utc)
        .isoformat()
    )

    attributes_fields = {
        "property_type": ("real_estate_type", "value_label"),
        "size": ("square", "value"),
        "rooms": ("rooms", "value"),
        "is_furnished": ("furnished", "value"),
        "charges_included": ("charges_included", "value"),
        "broker_fee": ("fai", "value"),
        "broker_fee_is_included": ("fai_included", "value"),
        "dpe_consumption": ("energy_rate", "value"),
        "dpe_emissions": ("ges", "value"),
    }

    def _get_attribute_field(
        ad: Mapping[str, Any], key: str, value_field: str
    ) -> Optional[str]:
        _dict = [d for d in ad["attributes"] if d["key"] == key]
        if not _dict:
            return None
        if len(_dict) > 1:
            msg = f"Unexpectedly got more than one match for attribute '{key}'."
            raise RuntimeError(msg)

        return _dict[0][value_field]

    data.update(
        {
            field: _get_attribute_field(ad, *attributes_fields[field])
            for field in attributes_fields
        }
    )
    if "is_furnished" in data:
        data["is_furnished"] = data["is_furnished"] == "1"
    if "broker_fee_is_included" in data:
        data["broker_fee_is_included"] = data["broker_fee_is_included"] == "1"
    if "dpe_consumption" in data:
        data["dpe_consumption"] = (
            data["dpe_consumption"] if data["dpe_consumption"] != "v" else None
        )
    if "dpe_emissions" in data:
        data["dpe_emissions"] = (
            data["dpe_emissions"] if data["dpe_emissions"] != "v" else None
        )

    if data.get("charges_included", "1") not in ("1", None):
        msg = f"Charges are not included: {ad}"
        raise NotImplementedError(msg)

    null_values = ["non renseigné"]
    data = {
        k: data[k] if str(data[k]).lower() not in null_values else None for k in data
    }

    location_fields = {
        "city": "city",
        "postal_code": "zipcode",
        "neighborhood": "city_label",
        "latitude": "lat",
        "longitude": "lng",
    }
    data.update(
        {
            field: ad.get("location", {}).get(location_fields[field])
            for field in location_fields
        }
    )

    for field in ["size", "rooms", "broker_fee"]:
        if (field not in data) or (not isinstance(data[field], str)):
            continue
        try:
            data[field] = float(data[field].replace(",", "."))
        except (KeyError, ValueError, AttributeError):
            data[field] = None

    # download the images
    is_aws_invocation = os.getenv("LAMBDA_TASK_ROOT") is not None
    if is_aws_invocation:
        s3 = boto3.client("s3")
        bucket = os.getenv("BUCKET_NAME")
    else:
        pogam_folder = os.path.join(os.path.expanduser("~/.pogam/"))

    folder_id = str(uuid.uuid4())
    remote_image_urls = ad.get("images", {}).get("urls", [])
    n_images = len(remote_image_urls)
    relative_image_paths: List[Optional[str]] = [None] * n_images
    width = max(len(str(n_images)), 2)
    for i, remote_image_url in enumerate(remote_image_urls):
        retries = 3
        while True:
            try:
                http_response = requests.get(
                    remote_image_url, headers=headers, proxies=proxies
                )
                break
            except requests.exceptions.RequestException:
                time.sleep(5)
                if retries <= 0:
                    msg = f"Could not download image #{i}."
                    logger.warning(msg)
                    break
                retries -= 1
        if retries <= 0:
            continue

        name = str(i + 1).zfill(width)
        _, extension = os.path.splitext(urlparse(remote_image_url).path)
        image_folder = f"leboncoin/{folder_id}/"
        relative_image_path = f"{image_folder}{name}{extension}"
        relative_image_paths[i] = relative_image_path

        if is_aws_invocation:
            try:
                s3.put_object(
                    Body=http_response.content, Bucket=bucket, Key=relative_image_path
                )
            except ClientError:
                msg = f"Could not download image #{i}."
                logger.exception(msg)
                continue
        else:
            os.makedirs(os.path.join(pogam_folder, image_folder), exist_ok=True)
            with open(os.path.join(pogam_folder, relative_image_path), "wb") as f:
                f.write(http_response.content)

        data["images"] = list(filter(None, relative_image_paths)) or None

    data["source"] = "leboncoin"

    property = Property.create(data)
    db.session.add(property)
    db.session.flush()
    data.update({"property_id": property.id})
    listing, is_new = Listing.get_or_create(**data)
    if is_new:
        db.session.add(listing)
        db.session.commit()

    return listing, is_new
