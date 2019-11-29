import json
import logging
import os
from typing import List

import boto3

from pogam import S3_TASKS_FILENAME, create_app, scrapers
from pogam.models import Listing

logger = logging.getLogger("pogam")
BUCKET_NAME = os.environ["BUCKET_NAME"]

# create app
app = create_app("cli")


def scrape(event, context):
    s3 = boto3.resource("s3")
    bucket = s3.Bucket(BUCKET_NAME)

    try:
        tasks = json.loads(bucket.Object(S3_TASKS_FILENAME).get()["Body"].read())
    except s3.meta.client.exceptions.NoSuchKey:
        tasks = []

    added_listings: List[Listing] = []
    seen_listings: List[Listing] = []
    failed_listings: List[str] = []
    for task in tasks:
        sources = task.pop("sources")
        for source in sources:
            scraper = getattr(scrapers, source)
            with app.app_context():
                results = scraper(**task)

                added_listings += [listing.url for listing in results["added"]]
                seen_listings += [listing.url for listing in results["seen"]]
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
    logger.info(msg)
