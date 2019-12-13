import json
import logging
import os

import boto3  # type: ignore
import markdown
import requests
from botocore.exceptions import ClientError
from python_markdown_slack import PythonMarkdownSlack
from requests.compat import urljoin

logger = logging.getLogger("pogam")

SLACK_API_HOST = "https://slack.com/api/"
CHARSET = "UTF-8"


def _pretty_print(listing):
    property_ = listing["property"]
    pp = (
        f"*<{listing['url']}|"
        f"{property_['type'].capitalize()} - "
        f"{property_['size']:,.0f}m² - "
        f"{listing['price']:,.0f}{listing['currency']}>*\n"
    )

    fields = [("rooms", "room"), ("bedrooms", "bed"), ("bathrooms", "bath")]
    for field, pretty_field in fields:
        field = property_.get(field, None)
        if field is None:
            continue
        if field == 0:
            pp += " • " if pp[-1] != "\n" else ""
            pp += f"No {pretty_field}s"
        elif int(field) == field:
            pp += " • " if pp[-1] != "\n" else ""
            pp += f"{int(field):d} {pretty_field}{'s' if field != 1 else ''}"
        else:
            pp += " • " if pp[-1] != "\n" else ""
            pp += f"{field:,.1f} {pretty_field}{'s' if field != 1 else ''}"
    pp += "\n"

    pp += (
        listing["description"][:140]
        + f"{'...' if len(listing['description']) > 140 else ''}"
    )
    return pp


def _location(listing):

    property_ = listing["property"]
    loc = ""
    neighborhood = property_.get("neighborhood", None)
    city = property_.get("city", None)
    postal_code = property_.get("postal_code", None)
    if neighborhood is not None:
        loc += neighborhood.capitalize()
    if city is not None:
        if neighborhood:
            loc += " - "
        loc += city.capitalize()
    if postal_code is not None:
        if neighborhood or city:
            loc += " - "
        loc += postal_code

    return loc


def slack(event, context):
    slack_token = os.getenv("SLACK_TOKEN")
    if slack_token is None:
        msg = "Environment variables'SLACK_TOKEN' is not set."
        logger.error(msg)
        return

    assert len(event) == 1
    assert len(event["Records"]) == 1
    event = event["Records"][0]
    channels = json.loads(event["Sns"]["MessageAttributes"]["slack"]["Value"])
    listings = json.loads(event["Sns"]["Message"])

    n_listings = len(listings)
    if n_listings == 0:
        return
    plural = "s" if n_listings > 1 else ""
    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"I found *{n_listings} new listing{plural}*!:man_dancing:",
            },
        }
    ]
    location_pin_url = "https://api.slack.com/img/blocks/bkb_template_images/tripAgentLocationMarker.png"  # noqa
    for listing in listings:
        gmap_link = (
            f"https://www.google.com/maps/search/?api=1&query="
            f"{requests.compat.quote_plus(_location(listing))}"
        )
        blocks += [
            {"type": "divider"},
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": _pretty_print(listing)},
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"<{gmap_link}|:round_pushpin:>{_location(listing)}",
                    }
                ],
            },
        ]

    url = urljoin(SLACK_API_HOST, "chat.postMessage")
    headers = {"Authorization": f"Bearer {slack_token}"}
    for channel in channels:
        data = {"channel": channel, "blocks": blocks, "unfurl_links": False}
        r = requests.post(url, headers=headers, json=data)
        logger.debug(r)
        logger.debug(r.text)


def email(event, context):
    from_ = os.getenv("EMAIL_SENDER")
    if from_ is None:
        msg = "Missing EMAIL_SENDER environment variable."
        logger.error(msg)
        return

    assert len(event) == 1
    assert len(event["Records"]) == 1
    event = event["Records"][0]
    to = json.loads(event["Sns"]["MessageAttributes"]["emails"]["Value"])
    listings = json.loads(event["Sns"]["Message"])

    n_listings = len(listings)
    if n_listings == 0:
        return
    plural = "s" if n_listings > 1 else ""

    subject = "New Listings in Pogam"
    message = f"I found *{n_listings} new listing{plural}*!\n\n"
    for listing in listings:
        gmap_link = (
            f"https://www.google.com/maps/search/?api=1&query="
            f"{requests.compat.quote_plus(_location(listing))}"
        )

        message += _pretty_print(listing).replace("\n", "\n\n")
        message += f"\n\n<{gmap_link}|📍>{_location(listing)}\n\n"
    message_html = markdown.markdown(message, extensions=[PythonMarkdownSlack()])

    email_client = boto3.client("ses")
    try:
        response = email_client.send_email(
            Source=from_,
            Destination={"ToAddresses": to},
            Message={
                "Subject": {"Data": subject, "Charset": CHARSET},
                "Body": {
                    "Html": {"Data": message_html, "Charset": CHARSET},
                    "Text": {"Data": message, "Charset": CHARSET},
                },
            },
        )
    except ClientError as e:
        logger.exception(e.response["Error"]["Message"])
    else:
        logger.debug(f"Email sent: {response['MessageId']}")
