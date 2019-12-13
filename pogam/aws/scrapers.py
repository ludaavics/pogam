import json
import logging
import os
from typing import List

import boto3  # type: ignore
import requests
from requests.compat import urljoin

from pogam import create_app, scrapers
from pogam.models import Listing

logger = logging.getLogger("pogam")


SLACK_API_HOST = "https://slack.com/api/"


def scrape(event, context):
    """
    Run a given scrape and store the results in the database.
    """
    search = event.get("search", None)
    if search is None:
        msg = "'event' must include a 'search' object."
        raise ValueError(msg)

    if not {"transaction", "post_codes", "sources"}.issubset(search):
        msg = (
            "The 'search' object must include at least "
            "'transaction', 'post_codes' and 'sources' objects."
        )
        raise ValueError(msg)
    sources = search.pop("sources")

    app = create_app("cli")
    added_listings: List[Listing] = []
    seen_listings: List[Listing] = []
    failed_listings: List[str] = []
    for source in sources:
        scraper = getattr(scrapers, source)
        with app.app_context():
            results = scraper(**search)

            added_listings += [listing.to_dict() for listing in results["added"]]
            seen_listings += results["seen"]
            failed_listings += results["failed"]

    num_added = len(added_listings)
    num_seen = len(seen_listings)
    num_failed = len(failed_listings)
    num_total = num_added + num_seen + num_failed
    msg = (
        f"All done!✨ 🍰 ✨\n"
        f"Of the {num_total} listings visited, we added {num_added}, "
        f"had already seen {num_seen} and choked on {num_failed}."
    )
    if failed_listings:
        msg += "\nFailed Listings:\n\n • {}".format("\n • ".join(failed_listings))
    logger.info(msg)

    # log to slack admin
    slack_admin = os.getenv("SLACK_ADMIN")
    slack_token = os.getenv("SLACK_TOKEN")
    if (slack_token is not None) and (slack_admin is not None):
        url = urljoin(SLACK_API_HOST, "chat.postMessage")
        data = {"channel": slack_admin, "text": msg, "unfurl_links": False}
        headers = {"Authorization": f"Bearer {slack_token}"}
        r = requests.post(url, headers=headers, json=data)
        logger.debug(r)
        logger.debug(r.text)

    # publish
    notify = event.get("notify", {})
    if not notify:
        msg = "Nobody to notify."
        logger.debug(msg)
        return

    sns = boto3.client("sns")
    new_listings_topic_arn = os.environ["NEW_LISTINGS_TOPIC_ARN"]
    message = json.dumps(added_listings)
    message_attributes = {
        k: {"DataType": "String.Array", "StringValue": json.dumps(notify[k])}
        for k in notify
    }
    pub = sns.publish(
        TopicArn=new_listings_topic_arn,
        Message=message,
        MessageAttributes=message_attributes,
    )
    logger.debug(f"Response : {str(pub)}")
