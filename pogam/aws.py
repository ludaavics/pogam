import json
import logging
import os
from typing import List
import uuid

import boto3

from pogam import create_app, scrapers
from pogam.models import Listing

logger = logging.getLogger("pogam")


def schedule(event, context):
    def _http_response(status_code, success, response, message):
        body = [{"success": success, "response": response, "message": message}]
        return {"statusCode": status_code, "body": json.dumps(body, indent=2)}

    # input validation
    data = json.loads(event.get("body", "{}"))
    if "schedule" not in data or "search" not in data:
        message = "Payload must include 'schedule' and 'search' objects."
        logging.exception(message)
        status_code = 422
        success = False
        response = ""
        return _http_response(status_code, success, response, message)

    search = data["search"]
    if not {"transaction", "post_codes", "sources"}.issubset(search):
        message = (
            "The 'search' object must include at least "
            "'transaction', 'post_codes' and 'sources'."
        )
        logging.exception(message)
        status_code = 422
        success = False
        response = ""
        return _http_response(status_code, success, response, message)
    transaction = search["transaction"]
    post_codes = search["post_codes"]
    sources = list(sorted(search["sources"]))

    # search for matching existing rules
    cloudwatch_events = boto3.client("events")
    rule_name = f"pogam_{transaction}_{'_'.join(post_codes)}_{'_'.join(sources)}_"
    existing_rules = cloudwatch_events.list_rules(NamePrefix=rule_name)["Rules"]
    rule_to_overwrite = None
    existing_uuids = []
    for existing_rule in existing_rules:
        existing_uuids.append(existing_rule["Name"].split("_")[-1])
        targets = cloudwatch_events.list_targets_by_rule(Rule=existing_rule["Name"])[
            "Targets"
        ]
        for target in targets:
            existing_search = json.loads(target["Input"])
            if search == existing_search["search"]:
                force = data.get("force", False)
                if force:
                    rule_to_overwrite = existing_rule["Name"]
                else:
                    message = (
                        "This search is already scheduled! To overwrite it "
                        "re-submit the request with 'force' set to True."
                    )
                    logger.exception(message)
                    status_code = 409
                    success = False
                    response = ""
                    return _http_response(status_code, success, response, message)

    # create a new rule
    _uuid = f"{str(uuid.uuid4()).split('-')[0]}"
    while _uuid in existing_uuids:
        _uuid = f"{str(uuid.uuid4()).split('-')[0]}"
    rule_name = rule_name + _uuid if rule_to_overwrite is None else rule_to_overwrite
    rule = cloudwatch_events.put_rule(
        Name=rule_name,
        ScheduleExpression=data["schedule"],
        State="ENABLED" if os.environ["STAGE"] == "prod" else "DISABLED",
    )
    target = cloudwatch_events.put_targets(
        Rule=rule_name,
        Targets=[
            {
                "Id": f"{rule_name}_target",
                "Arn": os.environ["SCRAPE_FUNCTION_ARN"],
                "Input": json.dumps({"search": data["search"]}),
            }
        ],
    )

    status_code = 200
    success = True
    response = {"rule": rule, "target": target}
    message = ""
    return _http_response(status_code, success, response, message)


def scrape(event, context):
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
