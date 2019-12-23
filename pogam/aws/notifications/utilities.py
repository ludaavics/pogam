import logging
import sys
import requests
from requests.compat import urljoin
import time

logger = logging.getLogger("pogam")
logger.setLevel(logging.DEBUG)
datefmt = "%d%b%Y %H:%M:%S"
fmt = "%(asctime)s - %(name)s.%(lineno)s - %(levelname)s - %(message)s"
formatter = logging.Formatter(fmt, datefmt)
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(formatter)
logger.addHandler = handler

SLACK_API_HOST = "https://slack.com/api/"


def slack_post_message(slack_token, channel, message, *, max_retries=10, **kwargs):
    if max_retries == 0:
        raise RuntimeError("Max Retries reached.")

    url = urljoin(SLACK_API_HOST, "chat.postMessage")
    headers = {"Authorization": f"Bearer {slack_token}"}
    data = {k: message[k] for k in message}
    data.update(kwargs)
    data.update({"channel": channel})
    r = requests.post(url, headers=headers, json=data)
    if r.status_code != 200:
        logger.debug(r)
        logger.debug(r.text)
    ok = r.json()["ok"]
    if ok:
        return

    if r.status_code == 429:
        sleep = int(r.headers["Retry-After"])
        time.sleep(sleep)

    return slack_post_message(
        channel, message, slack_token=slack_token, max_retries=max_retries - 1, **kwargs
    )
