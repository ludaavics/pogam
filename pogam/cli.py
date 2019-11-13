from . import create_app, scrape
import logging
import click_log  # type: ignore
import click
from typing import Iterable

logger = logging.getLogger("pogam")
click_log.basic_config(logger)
app = create_app()

PROPERTY_TYPES = ["apartment", "house", "parking", "store"]
SOURCES = ["seloger"]


@click.group()
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
    Scrape listings matching the search critera.
    """
    if not sources:
        sources = SOURCES
    for source in sources:
        click.echo(f"Scraping {source}...")
        scraper = getattr(scrape, source)
        with app.app_context():
            scraper(
                transaction,
                post_codes,
                property_types=property_types,
                min_price=min_price,
                max_price=max_price,
                min_size=min_size,
                min_rooms=min_rooms,
                max_rooms=max_rooms,
                min_beds=min_beds,
                max_beds=max_beds,
            )


cli.add_command(scrape_cmd, name="scrape")
