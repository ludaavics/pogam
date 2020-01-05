import json
import logging
import os
import uuid

import boto3  # type: ignore

logger = logging.getLogger("pogam")


def _jsonify(status_code, data, message):
    body = {"data": data, "message": message}
    return {"statusCode": status_code, "body": json.dumps(body, indent=2)}


def create(event, context):
    """
    Create a rule to scrape a given search on a given schedule.
    """
    stage = os.environ["STAGE"]
    data = json.loads(event.get("body", "{}"))
    if "schedule" not in data or "search" not in data:
        response_message = "Payload must include 'schedule' and 'search' objects."
        logging.exception(response_message)
        status_code = 422
        response_data = ""
        return _jsonify(status_code, response_data, response_message)

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
    transaction = search["transaction"]
    post_codes = search["post_codes"]
    sources = list(sorted(search["sources"]))

    # search for matching existing rules
    cloudwatch_events = boto3.client("events")
    rule_name = (
        f"pogam-{stage}-{transaction}-{'-'.join(post_codes)}-{'-'.join(sources)}-"
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
                    response_message = (
                        "This search is already scheduled! To overwrite it "
                        "re-submit the request with 'force' set to true."
                    )
                    logger.error(response_message)
                    status_code = 409
                    response_data = ""
                    return _jsonify(status_code, response_data, response_message)

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
    notify = data.get("notify", {})
    target = cloudwatch_events.put_targets(
        Rule=rule_name,
        Targets=[
            {
                "Id": f"{rule_name}_target",
                "Arn": os.environ["SCRAPE_FUNCTION_ARN"],
                "Input": json.dumps({"search": search, "notify": notify}),
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
    response_data = [
        {"name": rule["Name"], "schedule": rule["ScheduleExpression"], "search": search}
    ]
    response_message = ""
    return _jsonify(status_code, response_data, response_message)


def list_(event, context):
    """
    List scheduled scrapes.
    """
    cloudwatch_events = boto3.client("events")
    rule_name = f"pogam-{os.environ['STAGE']}-"
    rules = cloudwatch_events.list_rules(NamePrefix=rule_name)["Rules"]
    response_data = []
    for rule in rules:
        targets = cloudwatch_events.list_targets_by_rule(Rule=rule["Name"])["Targets"]
        assert len(targets) == 1
        data = json.loads(targets[0]["Input"])
        response_data += [
            {
                "name": rule["Name"],
                "schedule": rule["ScheduleExpression"],
                "search": data["search"],
                "notify": data["notify"],
            }
        ]

    status_code = 200
    response_message = ""
    return _jsonify(status_code, response_data, response_message)


def delete(event, context):
    """
    Delete a given scheduled scrape.
    """
    cloudwatch_events = boto3.client("events")
    rule_name = event["pathParameters"]["rule_name"]
    rules = cloudwatch_events.list_rules(NamePrefix=rule_name)["Rules"]
    if len(rules) != 1:
        if len(rules) == 0:
            response_message = f"Rule '{rule_name}' not found."
        else:
            response_message = (
                f"Expected to find exactly one rule matching '{rule_name}'. "
                f"Found {len(rules)} instead."
            )
        status_code = 404
        response_data = {"rules": rules}
        return _jsonify(status_code, response_data, response_message)

    rule = rules[0]
    targets = cloudwatch_events.list_targets_by_rule(Rule=rule["Name"])["Targets"]
    target_deletion = cloudwatch_events.remove_targets(
        Rule=rule["Name"], Ids=[target["Id"] for target in targets]
    )
    if target_deletion["FailedEntryCount"] != 0:
        status_code = 500
        response_data = target_deletion
        response_message = f"Could not remove all the targets from rule {rule_name}."
        return _jsonify(status_code, response_data, response_message)

    cloudwatch_events.delete_rule(Name=rule_name)
    status_code = 204
    response_data = {}
    response_message = ""
    return _jsonify(status_code, response_data, response_message)
