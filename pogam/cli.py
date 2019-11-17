import logging
from typing import Iterable, List

import click
import click_log  # type: ignore

from . import color, create_app, scrapes
from .models import Listing

logger = logging.getLogger("pogam")
click_log.basic_config(logger)
app = create_app("cli")

TRANSACTION_TYPES = ["rent", "buy"]
PROPERTY_TYPES = ["apartment", "house", "parking", "store"]
SOURCES = ["seloger"]


@click.group()
@click.version_option()
@click_log.simple_verbosity_option(logger)
def cli():
    pass


@click.command()
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
        scraper = getattr(scrapes, source)
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


cli.add_command(scrape_cmd, name="scrape")
