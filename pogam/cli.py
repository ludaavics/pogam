import logging
import os
from typing import Iterable, List

import click
import click_log  # type: ignore
import requests
from requests.compat import urljoin  # type: ignore

from . import SOURCES, create_app, scrapers
from .models import Listing

logger = logging.getLogger("pogam")
click_log.basic_config(logger)
app = create_app("cli")

TRANSACTION_TYPES = ["rent", "buy"]
PROPERTY_TYPES = ["apartment", "house", "parking", "store"]


# terminal colors
class color:
    RED = "\033[31m"
    GREEN = "\033[32m"
    PURPLE = "\033[95m"
    CYAN = "\033[96m"
    DARKCYAN = "\033[36m"
    BLUE = "\033[94m"
    LIGHT_GREEN = "\033[92m"
    YELLOW = "\033[93m"
    LIGHT_RED = "\033[91m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"
    END = "\033[0m"


@click.group()
@click.version_option()
@click_log.simple_verbosity_option(logger)
def cli():
    pass


@cli.command(name="scrape")
@click.argument("transaction")
@click.argument("post_codes", nargs=-1)
@click.option(
    "--type",
    "property_types",
    multiple=True,
    type=click.Choice(PROPERTY_TYPES, case_sensitive=False),
    default=["apartment", "house"],
    help="Type of property.",
)
@click.option("--min-price", type=float, help="Minimum property price.")
@click.option("--max-price", type=float, help="Maximum property price.")
@click.option("--min-size", type=float, help="Minimum property size, in square meters.")
@click.option("--max-size", type=float, help="Maximum property size, in square meters.")
@click.option("--min-rooms", type=float, help="Minimum number of rooms.")
@click.option("--max-rooms", type=float, help="Maximum number of rooms.")
@click.option("--min-beds", type=float, help="Minimum number of bedrooms.")
@click.option("--max-beds", type=float, help="Maximum number of bedrooms.")
@click.option(
    "--num-results",
    type=int,
    default=100,
    show_default=True,
    help="Approximate maximum number of listings to add to the database.",
)
@click.option(
    "--max-duplicates",
    type=int,
    default=25,
    help=(
        "Stop further scrapes once we see this many consecutive results that are "
        "already in the database."
    ),
)
@click.option(
    "--sources",
    multiple=True,
    type=click.Choice(SOURCES, case_sensitive=False),
    help="Sources to scrape.",
)
def scrape_cmd(
    transaction: str,
    post_codes: Iterable[str],
    property_types: Iterable[str],
    min_price: float,
    max_price: float,
    min_size: float,
    max_size: float,
    min_rooms: float,
    max_rooms: float,
    min_beds: float,
    max_beds: float,
    num_results: int,
    max_duplicates: int,
    sources: Iterable[str],
):
    """
    Scrape offers for a TRANSACTION in the given POST_CODES.

    TRANSACTION is 'rent' or 'buy'.
    POSTCODES are postal or zip codes of the search.
    """
    if transaction.lower() not in TRANSACTION_TYPES:
        raise ValueError(f"Unexpected transaction type {transaction}.")
    if not sources:
        sources = SOURCES
    added_listings: List[Listing] = []
    seen_listings: List[Listing] = []
    failed_listings: List[str] = []
    for source in sources:
        logger.info(f"Scraping {source}...")
        scraper = getattr(scrapers, source)
        with app.app_context():
            results = scraper(
                transaction,
                post_codes,
                property_types=property_types,
                min_price=min_price,
                max_price=max_price,
                min_size=min_size,
                max_size=max_size,
                min_rooms=min_rooms,
                max_rooms=max_rooms,
                min_beds=min_beds,
                max_beds=max_beds,
                num_results=num_results,
                max_duplicates=max_duplicates,
            )
            added_listings += [listing.url for listing in results["added"]]
            seen_listings += [listing.url for listing in results["seen"]]
            failed_listings += results["failed"]

    num_added = len(added_listings)
    num_seen = len(seen_listings)
    num_failed = len(failed_listings)
    num_total = num_added + num_seen + num_failed
    msg = (
        f"{color.BOLD}All done!✨ 🍰 ✨{color.END}\n"
        f"Of the {num_total} listings visited, we added {num_added}, "
        f"had already seen {num_seen} and choked on {num_failed}."
    )
    click.echo(msg)


@cli.group()
def schedule():
    """Schedule scrapes to run automatically."""


@schedule.command(name="add")
@click.argument("transaction")
@click.argument("post_codes", nargs=-1)
@click.option(
    "--type",
    "property_types",
    multiple=True,
    type=click.Choice(PROPERTY_TYPES, case_sensitive=False),
    default=["apartment", "house"],
    help="Type of property.",
)
@click.option("--min-price", type=float, help="Minimum property price.")
@click.option("--max-price", type=float, help="Maximum property price.")
@click.option("--min-size", type=float, help="Minimum property size, in square meters.")
@click.option("--max-size", type=float, help="Maximum property size, in square meters.")
@click.option("--min-rooms", type=float, help="Minimum number of rooms.")
@click.option("--max-rooms", type=float, help="Maximum number of rooms.")
@click.option("--min-beds", type=float, help="Minimum number of bedrooms.")
@click.option("--max-beds", type=float, help="Maximum number of bedrooms.")
@click.option(
    "--num-results",
    type=int,
    default=100,
    show_default=True,
    help="Approximate maximum number of listings to add to the database.",
)
@click.option(
    "--max-duplicates",
    type=int,
    default=25,
    help=(
        "Stop further scrapes once we see this many consecutive results that are "
        "already in the database."
    ),
)
@click.option(
    "--sources",
    multiple=True,
    type=click.Choice(SOURCES, case_sensitive=False),
    help="Sources to scrape.",
)
@click.option(
    "--schedule",
    type=str,
    help="Schedule following the rate or cron syntax.",
    default="cron(0 0/6 * * ? *)",
    show_default=True,
)
@click.option("--force", default=False, is_flag=True)
def schedule_add(
    transaction: str,
    post_codes: Iterable[str],
    property_types: Iterable[str],
    min_price: float,
    max_price: float,
    min_size: float,
    max_size: float,
    min_rooms: float,
    max_rooms: float,
    min_beds: float,
    max_beds: float,
    num_results: int,
    max_duplicates: int,
    sources: Iterable[str],
    schedule: str,
    force: bool,
):
    """
    Set a schedule for scraping TRANSACTIONs in the given POST_CODES.

    TRANSACTION is 'rent' or 'buy'.
    POSTCODES are postal or zip codes of the search.
    """
    if transaction.lower() not in TRANSACTION_TYPES:
        raise ValueError(f"Unexpected transaction type {transaction}.")
    if not sources:
        sources = SOURCES

    host = os.environ["POGAM_AWS_API_HOST"]
    has_trailing_slash = host[-1] == "/"
    host = host if has_trailing_slash else host + "/"

    data = {
        "force": force,
        "search": {
            "transaction": transaction,
            "post_codes": post_codes,
            "property_types": property_types,
            "min_price": min_price,
            "max_price": max_price,
            "min_size": min_size,
            "max_size": max_size,
            "min_rooms": min_rooms,
            "max_rooms": max_rooms,
            "min_beds": min_beds,
            "max_beds": max_beds,
            "num_results": num_results,
            "max_duplicates": max_duplicates,
            "sources": sources,
        },
        "schedule": schedule,
    }

    url = urljoin(host, "schedules")
    response = requests.post(url, json=data)
    if response.status_code >= 400:
        msg = (
            f"{color.LIGHT_RED}Something went wrong.{color.END} "
            f"Got status code {response.status_code} and reponse {response.text}."
        )
        click.echo(msg)
        return

    logger.debug(response.text)
    msg = f"{color.BOLD}✨All done! 🍰 The search has been scheduled. ✨{color.END}"
    click.echo(msg)


@schedule.command(name="list")
def schedule_list():
    """List all scheduled tasks."""
    host = os.environ["POGAM_AWS_API_HOST"]
    has_trailing_slash = host[-1] == "/"
    host = host if has_trailing_slash else host + "/"
    url = urljoin(host, "schedules")
    response = requests.get(url)
    if response.status_code >= 400:
        msg = (
            f"{color.LIGHT_RED}Something went wrong.{color.END} "
            f"Got status code {response.status_code} and reponse {response.text}."
        )
        click.echo(msg)
        return

    click.echo(response.text)
    return response.text


@schedule.command(name="delete")
@click.argument("rule_name")
def schedule_delete(rule_name):
    """Delete a scheduled task."""
    host = os.environ["POGAM_AWS_API_HOST"]
    has_trailing_slash = host[-1] == "/"
    host = host if has_trailing_slash else host + "/"
    url = urljoin(host, f"schedules/{rule_name}")
    response = requests.delete(url)
    if response.status_code >= 400:
        msg = (
            f"{color.LIGHT_RED}Something went wrong.{color.END} "
            f"Got status code {response.status_code} and reponse {response.text}."
        )
        click.echo(msg)
        return
    elif response.status_code == 204:
        logger.debug(response.text)
        msg = f"{color.BOLD}✨All done! 🍰 The search has been deleted. ✨{color.END}"
        click.echo(msg)
    else:
        click.echo(response.text)


@schedule.command(name="clear")
def schedule_clear():
    """Clear all scheduled tasks."""
    # TO DO: call schedule_list directly
    host = os.environ["POGAM_AWS_API_HOST"]
    has_trailing_slash = host[-1] == "/"
    host = host if has_trailing_slash else host + "/"
    url = urljoin(host, "schedules")
    response = requests.get(url)
    if response.status_code >= 400:
        msg = (
            f"{color.LIGHT_RED}Something went wrong.{color.END} "
            f"Got status code {response.status_code} and reponse {response.text}."
        )
        click.echo(msg)
        return

    tasks = response.json()["response"]
    failed = []
    for task in tasks:
        url = urljoin(host, f"schedules/{task['name']}")
        response = requests.delete(url)
        if response.status_code >= 400:
            failed += task["name"]

    n_tasks = len(tasks)
    done = n_tasks - len(failed)
    if failed:
        msg = (
            f"{color.LIGHT_RED}Deleted {done} out of {n_tasks} tasks. "
            f"Failed to delete {', '.join(failed)}.{color.END}"
        )
        click.echo(msg)
    else:
        msg = f"{color.BOLD}✨All done! 🍰 Deleted {n_tasks} tasks.✨{color.END}"
        click.echo(msg)
