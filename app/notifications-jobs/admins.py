import logging
import os

import boto3  # type: ignore
from botocore.exceptions import ClientError
import requests
from requests.compat import urljoin

logger = logging.getLogger("pogam")


SLACK_API_HOST = "https://slack.com/api/"
CHARSET = "UTF-8"


def slack(event, context):
    print(event)
    slack_admin = os.getenv("SLACK_ADMIN")
    slack_token = os.getenv("SLACK_TOKEN")
    if (slack_token is None) or (slack_admin is None):
        msg = "Missing SLACK_ADMIN and/or SLACK_TOKEN environment variables."
        logger.error(msg)
        return

    assert len(event) == 1
    assert len(event["Records"]) == 1
    message = event["Records"][0]["Sns"]["Message"]

    url = urljoin(SLACK_API_HOST, "chat.postMessage")
    data = {"channel": slack_admin, "text": message, "unfurl_links": False}
    headers = {"Authorization": f"Bearer {slack_token}"}
    r = requests.post(url, headers=headers, json=data)
    logger.debug(r)
    logger.debug(r.text)


def email(event, context):
    print(event)
    to = os.getenv("EMAIL_ADMINS").split(",")
    from_ = os.getenv("EMAIL_SENDER")
    if (from_ is None) or (to is None):
        msg = "Missing EMAIL_ADMINS and/or EMAIL_SENDER environment variable(s)."
        logger.error(msg)

    message = event["Records"][0]["Sns"]["Message"]
    email_client = boto3.client("ses")
    try:
        response = email_client.send_email(
            Source=from_,
            Destination={"ToAddresses": to},
            Message={
                "Subject": {"Data": "Status Update", "Charset": CHARSET},
                "Body": {"Text": {"Data": message, "Charset": CHARSET}},
            },
        )
    except ClientError as e:
        logger.exception(e.response["Error"]["Message"])
    else:
        logger.debug(f"Email sent: {response['MessageId']}")
