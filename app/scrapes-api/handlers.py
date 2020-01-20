import json
import logging
import os
from typing import List

import boto3  # type: ignore
from botocore.exceptions import ClientError

from pogam import create_app, scrapers
from pogam.models import Listing

logger = logging.getLogger("pogam")


def _jsonify(status_code, data, message):
    body = {"data": data, "message": message}
    return {"statusCode": status_code, "body": json.dumps(body, indent=2)}


def run(event, context):
    """
    Run a given scrape and store the results in the database.
    """
    if "search" in event:
        search = event.get("search", None)
    elif "Records" in event:
        records = event.get("Records", [])
        if len(records) > 1:
            msg = f"Unexpectedly got multiple SNS events."
            raise ValueError(msg)
        sns_message = json.loads(records[0].get("Sns", {}).get("Message", ""))
        if not sns_message:
            msg = "No SNS message found."
            raise ValueError(msg)
        search = sns_message.get("search", None)
    else:
        msg = f"Unexpected event:\n{event}"
        raise RuntimeError(msg)

    if search is None:
        msg = (
            "'event' must include a 'search' object or be a "
            "SNS event with a search object in the message"
        )
        raise ValueError(msg)

    if not {"transaction", "post_codes", "sources"}.issubset(search):
        msg = (
            "The 'search' object must include at least "
            "'transaction', 'post_codes' and 'sources' objects."
        )
        raise ValueError(msg)
    sources = search.pop("sources")

    app = create_app()
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

    # publish result info to admins topic
    sns = boto3.client("sns")
    admins_topic_arn = os.getenv("ADMINS_TOPIC_ARN")
    try:
        pub = sns.publish(TopicArn=admins_topic_arn, Message=msg)
    except ClientError as e:
        msg = f"Could not publish to admins topic:\n{e}"
        logging.warn(msg)

    # publish new listings to relevant topic
    notify = event.get("notify", {})
    if not notify:
        msg = "Nobody to notify."
        logger.debug(msg)
        return

    new_listings_topic_arn = os.getenv("NEW_LISTINGS_TOPIC_ARN")
    if new_listings_topic_arn is not None:
        msg = f"No topic to send notifications."
        logger.warn(msg)
        return
    message = json.dumps(added_listings)
    message_attributes = {
        k: {"DataType": "String.Array", "StringValue": json.dumps(notify[k])}
        for k in notify
    }
    try:
        pub = sns.publish(
            TopicArn=new_listings_topic_arn,
            Message=message,
            MessageAttributes=message_attributes,
        )
        logger.debug(f"Response : {str(pub)}")
    except ClientError as e:
        msg = f"Could not publish to new listing topic:\n{e}"
        logging.warn(msg)


def create(event, context):
    """Run a one-off scrape."""
    data = json.loads(event.get("body", "{}"))

    search = data["search"]
    if not {"transaction", "post_codes", "sources"}.issubset(search):
        response_message = (
            "The 'search' object must include at least "
            "'transaction', 'post_codes' and 'sources'."
        )
        logging.exception(response_message)
        status_code = 422
        response_data = ""
        return _jsonify(status_code, response_data, response_message)

    # publish the job
    sns = boto3.client("sns")
    jobs_topic_arn = os.getenv("JOBS_TOPIC_ARN")
    pub = sns.publish(TopicArn=jobs_topic_arn, Message=json.dumps(data))
    logger.debug(f"Scrape job published: {str(pub)}")

    # send response
    status_code = 201
    response_data = {"sns_response": pub}
    response_message = ""
    return _jsonify(status_code, response_data, response_message)
