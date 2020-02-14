import json
import logging
import os
import stat
import subprocess
import sys
from datetime import datetime, timedelta
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
SERVICES = [
    "shared-resources",
    "users-api",
    "scrapes-api",
    "scrape-schedules-api",
    "notifications-jobs",
]


class Color:
    """Terminal Colors"""

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
    Run (local) scrape for offers for a TRANSACTION in the given POST_CODES.

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
            added_listings += results["added"]
            seen_listings += results["seen"]
            failed_listings += results["failed"]

    num_added = len(added_listings)
    num_seen = len(seen_listings)
    num_failed = len(failed_listings)
    num_total = num_added + num_seen + num_failed
    msg = (
        f"{Color.BOLD}All done!✨ 🍰 ✨{Color.END}\n"
        f"Of the {num_total} listings visited, we added {num_added}, "
        f"had already seen {num_seen} and choked on {num_failed}."
    )
    click.echo(msg)


# ------------------------------------------------------------------------------------ #
#                                     App Commands                                     #
# ------------------------------------------------------------------------------------ #
@cli.group(name="app")
def app_cli():
    """Manage Pogam's web app."""


@app_cli.group(name="scrape")
def app_scrape_cli():
    """Manage scrapes in Pogam's web app."""


def _host():
    host = os.getenv("POGAM_API_HOST")
    if host is None:
        msg = "POGAM_API_HOST environment variable not found."
        raise ValueError(msg)
    has_trailing_slash = host[-1] == "/"
    host = host if has_trailing_slash else host + "/"
    return host


# ---------------------------------- App Management ---------------------------------- #
@app_cli.command(name="deploy")
@click.argument("stage")
def deploy(stage: str):
    """Deploy the app to the given stage."""
    here = os.path.dirname(__file__)
    app_folder = os.path.abspath(os.path.join(here, "..", "app"))

    for service in SERVICES:
        folder = os.path.join(app_folder, service)
        logger.info(f"Deploying {service} service to stage {stage}...")
        process = subprocess.run(
            ["sls", "deploy", "--stage", stage], cwd=folder, capture_output=True
        )
        if process.returncode == 0:
            logger.debug(process.stdout.decode("utf-8"))
        else:
            raise RuntimeError(process.stdout.decode("utf-8"))


@app_cli.command(name="remove")
@click.argument("stage")
def remove(stage: str):
    """Remove the app from the given stage."""
    here = os.path.dirname(__file__)
    app_folder = os.path.abspath(os.path.join(here, "..", "app"))

    for service in reversed(SERVICES):
        folder = os.path.join(app_folder, service)
        logger.info(f"Removing {service} service from stage {stage}...")
        process = subprocess.run(
            ["sls", "remove", "--stage", stage], cwd=folder, capture_output=True
        )
        if process.returncode == 0:
            logger.debug(process.stdout.decode("utf-8"))
        else:
            logger.warning(process.stdout.decode("utf-8"))


@app_cli.command(name="login")
@click.option("--email", prompt=True)
@click.option("--password", prompt=True, hide_input=True)
@click.option(
    "--alias", prompt="Enter an alias to remember this account by", default="default"
)
def login(email: str, password: str, alias: str):
    """Log into the web app."""
    folder = os.path.expanduser("~/.pogam/")
    os.makedirs(folder, exist_ok=True)

    host = _host()
    url = urljoin(host, "v1/users/authenticate")
    data = {"email": email, "password": password}
    response = requests.post(url, json=data)
    if response.status_code >= 400:
        try:
            msg = f"{Color.LIGHT_RED}{response.json()['message']}{Color.END}\n"
            click.echo(msg)
            sys.exit(1)
        except (json.JSONDecodeError, KeyError):
            msg = (
                f"{Color.LIGHT_RED}Something went wrong.{Color.END}\n"
                f"Got status code {response.status_code} and reponse {response.text}."
            )
            click.echo(msg)
            sys.exit(1)
    data = response.json()["data"]
    credentials = {
        "token": data["token"],
        "expires_at": (
            datetime.utcnow() + timedelta(seconds=data["expires_in"])
        ).isoformat(),
    }
    credentials_path = os.path.join(folder, "credentials")
    try:
        with open(credentials_path, "r") as f:
            all_credentials = json.load(f)
    except FileNotFoundError:
        all_credentials = {}
    all_credentials.update({alias: credentials})
    with open(credentials_path, "w") as f:
        json.dump(all_credentials, f, indent=2)

    permission = stat.S_IREAD | stat.S_IWUSR  # rw-------
    os.chmod(credentials_path, permission)

    click.echo(f"{Color.BOLD}Logged in successfully.{Color.END}")


@app_cli.command(name="logout")
@click.option(
    "--alias",
    default="default",
    show_default=True,
    help="Alias of the account to log out of.",
)
def logout(alias):
    """Log out of the web app."""
    folder = os.path.expanduser("~/.pogam/")
    credentials_path = os.path.join(folder, "credentials")
    try:
        with open(credentials_path, "r") as f:
            all_credentials = json.load(f)
    except FileNotFoundError:
        all_credentials = {}
    try:
        all_credentials.pop(alias)
    except KeyError:
        click.echo(f"{Color.BOLD}Alias '{alias}' not found.{Color.END}")
        return
    with open(credentials_path, "w") as f:
        json.dump(all_credentials, f, indent=2)
    click.echo(f"{Color.BOLD}Logged out successfully.{Color.END}")


def _token(alias="default"):
    folder = os.path.expanduser("~/.pogam/")
    credentials_path = os.path.join(folder, "credentials")
    with open(credentials_path, "r") as f:
        credentials = json.load(f).get(alias)
    if not credentials:
        msg = (
            f"{Color.LIGHT_RED}Account '{alias}' is not logged in. "
            f"Please log in and try again.{Color.END}"
        )
        click.echo(msg)
        sys.exit(1)
    if datetime.utcnow() > datetime.fromisoformat(credentials["expires_at"]):
        msg = (
            f"{Color.LIGHT_RED}Your session has expired. "
            f"Please log back in and try again.{Color.END}"
        )
        click.echo(msg)
        sys.exit(1)
    return credentials["token"]


# -------------------------------- App One-Off Scrape -------------------------------- #
@app_scrape_cli.command(name="create")
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
    "--alias", default="default", show_default=True, help="Account alias",
)
def scrapes_create(
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
    alias: str,
):
    """
    Run a one-off scrape of TRANSACTIONs in the given POST_CODES in the app.

    TRANSACTION is 'rent' or 'buy'.
    POSTCODES are postal or zip codes of the search.
    """
    if transaction.lower() not in TRANSACTION_TYPES:
        raise ValueError(f"Unexpected transaction type {transaction}.")
    if not sources:
        sources = SOURCES
    host = _host()
    token = _token(alias=alias)

    url = urljoin(host, "v1/scrapes")
    headers = {"Authorization": token}
    data = {
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
        }
    }

    response = requests.post(url, json=data, headers=headers)
    if response.status_code >= 400:
        try:
            msg = f"{Color.LIGHT_RED}{response.json()['message']}{Color.END}\n"
            click.echo(msg)
            sys.exit(1)
        except (json.JSONDecodeError, KeyError):
            msg = (
                f"{Color.LIGHT_RED}Something went wrong.{Color.END}\n"
                f"Got status code {response.status_code} and reponse {response.text}."
            )
            click.echo(msg)
            sys.exit(1)

    try:
        response_data = response.json()["data"]
    except json.decoder.JSONDecodeError:
        response_data = {}
    sns_message_id = response_data.get("sns_response", {}).get("MessageId")
    sns_message_id = f"\n(message id: {sns_message_id})" if sns_message_id else ""
    msg = (
        f"{Color.BOLD}🛠️The scrape has been kicked off.🛠️{Color.END}"
        f"{sns_message_id}"
    )
    click.echo(msg)


# -------------------------- App Scrape Scheduling Commands -------------------------- #
@app_scrape_cli.group(name="schedule")
def scrape_schedules():
    """Manage the app's scraping schedule."""


@scrape_schedules.command(name="create")
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
@click.option("--slack", multiple=True, help="Slack channels to notify.")
@click.option("--email", multiple=True, help="Email addresses to notify.")
@click.option(
    "--schedule",
    type=str,
    help="Schedule following the rate or cron syntax.",
    default="cron(0 3/6 * * ? *)",
    show_default=True,
)
@click.option("--force", default=False, is_flag=True)
@click.option(
    "--alias", default="default", show_default=True, help="Account alias",
)
def scrape_schedules_create(
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
    slack: Iterable[str],
    email: Iterable[str],
    force: bool,
    alias: str,
):
    """
    Add the task of scraping TRANSACTIONs in the given POST_CODES to the app's schedule.

    TRANSACTION is 'rent' or 'buy'.
    POSTCODES are postal or zip codes of the search.
    """
    if transaction.lower() not in TRANSACTION_TYPES:
        raise ValueError(f"Unexpected transaction type {transaction}.")
    if not sources:
        sources = SOURCES
    host = _host()
    token = _token(alias=alias)

    notify = {}
    if slack:
        notify["slack"] = slack
    if email:
        notify["emails"] = email

    url = urljoin(host, "v1/scrape-schedules")
    headers = {"Authorization": token}
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
        "notify": notify,
    }
    response = requests.post(url, json=data, headers=headers)
    if response.status_code >= 400:
        try:
            msg = f"{Color.LIGHT_RED}{response.json()['message']}{Color.END}\n"
            click.echo(msg)
            sys.exit(1)
        except (json.JSONDecodeError, KeyError):
            msg = (
                f"{Color.LIGHT_RED}Something went wrong.{Color.END}\n"
                f"Got status code {response.status_code} and reponse {response.text}."
            )
            click.echo(msg)
            sys.exit(1)

    logger.debug(response.text)
    msg = f"{Color.BOLD}✨All done! 🍰 The search has been scheduled. ✨{Color.END}"
    click.echo(msg)


@scrape_schedules.command(name="list")
@click.option(
    "--alias", default="default", show_default=True, help="Account alias",
)
def scrape_schedules_list(alias: str):
    """List all the scraping tasks scheduled in the app."""
    host = _host()
    token = _token(alias=alias)

    url = urljoin(host, "v1/scrape-schedules")
    headers = {"Authorization": token}
    response = requests.get(url, headers=headers)
    if response.status_code >= 400:
        try:
            msg = f"{Color.LIGHT_RED}{response.json()['message']}{Color.END}\n"
            click.echo(msg)
            sys.exit(1)
        except (json.JSONDecodeError, KeyError):
            msg = (
                f"{Color.LIGHT_RED}Something went wrong.{Color.END}\n"
                f"Got status code {response.status_code} and reponse {response.text}."
            )
            click.echo(msg)
            sys.exit(1)
    try:
        data = json.dumps(response.json()["data"], indent=2)
    except (json.JSONDecodeError, KeyError):
        data = response.text
    click.echo(data)


@scrape_schedules.command(name="delete")
@click.argument("rule_name")
@click.option(
    "--alias", default="default", show_default=True, help="Account alias",
)
def schedule_delete(rule_name: str, alias: str):
    """Delete a scheduled task from the app."""
    host = _host()
    token = _token(alias=alias)

    url = urljoin(host, f"v1/scrape-schedules/{rule_name}")
    headers = {"Authorization": token}
    response = requests.delete(url, headers=headers)
    if response.status_code >= 400:
        try:
            msg = f"{Color.LIGHT_RED}{response.json()['message']}{Color.END}\n"
            click.echo(msg)
            sys.exit(1)
        except (json.JSONDecodeError, KeyError):
            msg = (
                f"{Color.LIGHT_RED}Something went wrong.{Color.END}\n"
                f"Got status code {response.status_code} and reponse {response.text}."
            )
            click.echo(msg)
            sys.exit(1)
    elif response.status_code == 204:
        logger.debug(response.text)
        msg = f"{Color.BOLD}✨All done! 🍰 The search has been deleted. ✨{Color.END}"
        click.echo(msg)

    click.echo(response.text)
    return response.text


@scrape_schedules.command(name="clear")
@click.option(
    "--alias", default="default", show_default=True, help="Account alias",
)
def schedule_clear(alias: str):
    """Clear all scheduled tasks from the app."""
    host = _host()
    token = _token(alias=alias)

    url = urljoin(host, "v1/scrape-schedules")
    headers = {"Authorization": token}
    response = requests.get(url, headers=headers)
    if response.status_code >= 400:
        try:
            msg = f"{Color.LIGHT_RED}{response.json()['message']}{Color.END}\n"
            click.echo(msg)
            sys.exit(1)
        except (json.JSONDecodeError, KeyError):
            msg = (
                f"{Color.LIGHT_RED}Something went wrong.{Color.END}\n"
                f"Got status code {response.status_code} and reponse {response.text}."
            )
            click.echo(msg)
            sys.exit(1)

    tasks = response.json()["data"]
    failed = []
    for task in tasks:
        url = urljoin(host, f"v1/scrape-schedules/{task['name']}")
        response = requests.delete(url, headers=headers)
        if response.status_code >= 400:
            failed.append(task["name"])

    n_tasks = len(tasks)
    done = n_tasks - len(failed)
    if failed:
        new_bullet = "\n  • "
        _failed = f"{new_bullet}{new_bullet.join(failed)}"
        msg = (
            f"{Color.LIGHT_RED}Deleted {done} out of {n_tasks} tasks. "
            f"Failed to delete: {_failed}.{Color.END}"
        )
        click.echo(msg)
    else:
        msg = f"{Color.BOLD}✨All done! 🍰 Deleted {n_tasks} tasks.✨{Color.END}"
        click.echo(msg)
