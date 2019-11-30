import json
import logging
import os
import uuid
from typing import List

import boto3  # type: ignore

from pogam import create_app, scrapers
from pogam.models import Listing

logger = logging.getLogger("pogam")


def _jsonify(status_code, response, message):
    body = {"response": response, "message": message}
    return {"statusCode": status_code, "body": json.dumps(body, indent=2)}


def schedules_add(event, context):
    """
    Create a rule to scrape a given search on a given schedule.
    """
    stage = os.environ["STAGE"]
    data = json.loads(event.get("body", "{}"))
    if "schedule" not in data or "search" not in data:
        message = "Payload must include 'schedule' and 'search' objects."
        logging.exception(message)
        status_code = 422
        response = ""
        return _jsonify(status_code, response, message)

    search = data["search"]
    if not {"transaction", "post_codes", "sources"}.issubset(search):
        message = (
            "The 'search' object must include at least "
            "'transaction', 'post_codes' and 'sources'."
        )
        logging.exception(message)
        status_code = 422
        response = ""
        return _jsonify(status_code, response, message)
    transaction = search["transaction"]
    post_codes = search["post_codes"]
    sources = list(sorted(search["sources"]))

    # search for matching existing rules
    cloudwatch_events = boto3.client("events")
    rule_name = (
        f"pogam-{stage}_{transaction}_{'_'.join(post_codes)}_{'_'.join(sources)}_"
    )
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
                        "re-submit the request with 'force' set to true."
                    )
                    logger.exception(message)
                    status_code = 409
                    response = ""
                    return _jsonify(status_code, response, message)

    # create a new rule
    _uuid = f"{str(uuid.uuid4()).split('-')[0]}"
    while _uuid in existing_uuids:
        _uuid = f"{str(uuid.uuid4()).split('-')[0]}"
    rule_name = rule_name + _uuid if rule_to_overwrite is None else rule_to_overwrite
    rule = cloudwatch_events.put_rule(
        Name=rule_name,
        ScheduleExpression=data["schedule"],
        State="ENABLED" if stage == "prod" else "DISABLED",
    )
    target = cloudwatch_events.put_targets(
        Rule=rule_name,
        Targets=[
            {
                "Id": f"{rule_name}_target",
                "Arn": os.environ["SCRAPE_FUNCTION_ARN"],
                "Input": json.dumps({"search": search}),
            }
        ],
    )

    # fetch the newly created rule
    rules = cloudwatch_events.list_rules(NamePrefix=rule_name)["Rules"]
    assert len(rules) == 1
    rule = rules[0]
    targets = cloudwatch_events.list_targets_by_rule(Rule=rule["Name"])["Targets"]
    assert len(targets) == 1
    search = json.loads(targets[0]["Input"])["search"]

    status_code = 201
    response = {
        "name": rule["Name"],
        "schedule": rule["ScheduleExpression"],
        "search": search,
    }
    message = ""
    return _jsonify(status_code, response, message)


def schedules_list(event, context):
    """
    List scheduled scrapes.
    """
    cloudwatch_events = boto3.client("events")
    rule_name = f"pogam-{os.environ['STAGE']}_"
    rules = cloudwatch_events.list_rules(NamePrefix=rule_name)["Rules"]
    response = []
    for rule in rules:
        targets = cloudwatch_events.list_targets_by_rule(Rule=rule["Name"])["Targets"]
        assert len(targets) == 1
        search = json.loads(targets[0]["Input"])["search"]
        response += [
            {
                "name": rule["Name"],
                "schedule": rule["ScheduleExpression"],
                "search": search,
            }
        ]

    status_code = 200
    message = ""
    return _jsonify(status_code, response, message)


def schedules_delete(event, context):
    """
    Delete a given scheduled scrape.
    """
    cloudwatch_events = boto3.client("events")
    rule_name = event["pathParameters"]["rule_name"]
    rules = cloudwatch_events.list_rules(NamePrefix=rule_name)["Rules"]
    if len(rules) != 1:
        if len(rules) == 0:
            message = f"Rule '{rule_name}' not found."
        else:
            message = (
                f"Expected to find exactly one rule matching '{rule_name}'. "
                f"Found {len(rules)} instead."
            )
        status_code = 404
        response = {"rules": rules}
        return _jsonify(status_code, response, message)

    rule = rules[0]
    targets = cloudwatch_events.list_targets_by_rule(Rule=rule["Name"])["Targets"]
    target_deletion = cloudwatch_events.remove_targets(
        Rule=rule["Name"], Ids=[target["Id"] for target in targets]
    )
    if target_deletion["FailedEntryCount"] != 0:
        status_code = 500
        response = target_deletion
        message = f"Could not remove all the targets from rule {rule_name}."
        return _jsonify(status_code, response, message)

    cloudwatch_events.delete_rule(Name=rule_name)
    status_code = 204
    response = {}
    message = ""
    return _jsonify(status_code, response, message)


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
