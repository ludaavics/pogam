import logging
import os

import requests
from requests.compat import urljoin


logger = logging.getLogger("pogam")


SLACK_API_HOST = "https://slack.com/api/"


def slack(event, context):
    slack_admin = os.getenv("SLACK_ADMIN")
    slack_token = os.getenv("SLACK_TOKEN")

    if (slack_token is None) or (slack_admin is None):
        msg = "Missing SLACK_ADMIN and/or SLACK_TOKEN environment variables."
        logger.debug(msg)
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
