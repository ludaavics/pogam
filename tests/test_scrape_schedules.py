import json
import logging
import re

import boto3
import pytest
from click.testing import CliRunner

from pogam.cli import cli

logger = logging.getLogger("pogam-tests")


# ------------------------------------------------------------------------------------ #
#                                       Fixtures                                       #
# ------------------------------------------------------------------------------------ #
@pytest.fixture
def cleanup_rules(stage):
    yield
    cloudwatch_events = boto3.client("events")
    rule_name = f"pogam-{stage}-"
    rules = cloudwatch_events.list_rules(NamePrefix=rule_name)["Rules"]
    for rule in rules:
        targets = cloudwatch_events.list_targets_by_rule(Rule=rule["Name"])["Targets"]
        if targets:
            target_deletion = cloudwatch_events.remove_targets(
                Rule=rule["Name"], Ids=[target["Id"] for target in targets]
            )
            assert (
                target_deletion["FailedEntryCount"] == 0
            ), f"Failed to delete some targets from {rule['Name']}."
        cloudwatch_events.delete_rule(Name=rule["Name"])


# ------------------------------------------------------------------------------------ #
#                                         Tests                                        #
# ------------------------------------------------------------------------------------ #
@pytest.mark.aws
@pytest.mark.parametrize(
    "transaction, post_codes, min_size, max_size, logged_in",
    [("rent", "92130", "29", "31", True), ("rent", "92130", "29", "31", False)],
)
def test_cli_app_scrape_schedule_crud(
    stage,
    cli_login,
    cli_temporary_logout,
    scrape_schedules_api_service,
    cleanup_rules,
    transaction,
    post_codes,
    min_size,
    max_size,
    logged_in,
    snapshot,
):
    """Scrape Schedules CRUD"""
    if not logged_in:
        cli_temporary_logout()
    runner = CliRunner()

    logger.info("Listing (empty) schedules...")
    cli_response = runner.invoke(
        cli, ["app", "scrape", "schedule", "list", "--alias", "test"],
    )
    assert cli_response.exit_code == (not logged_in), cli_response.output
    empty_schedule_response = cli_response.output
    snapshot.assert_match(empty_schedule_response)

    logger.info("Adding new scrape schedules...")
    for _transaction, _min_size, _max_size in [
        (transaction, min_size, max_size),
        (transaction, float(min_size) - 1, max_size),
        (transaction, float(min_size) - 2, max_size),
    ]:
        cli_response = runner.invoke(
            cli,
            [
                "app",
                "scrape",
                "schedule",
                "create",
                _transaction,
                post_codes,
                "--min-size",
                _min_size,
                "--max-size",
                _max_size,
                "--alias",
                "test",
            ],
        )
        assert cli_response.exit_code == (not logged_in), cli_response.output
        snapshot.assert_match(cli_response.output)

    logger.info("Listing the new schedules...")
    cli_response = runner.invoke(
        cli, ["app", "scrape", "schedule", "list", "--alias", "test"],
    )
    assert cli_response.exit_code == (not logged_in), cli_response.output
    original_names = re.findall(f"pogam-{stage}[-\\w]+", cli_response.output)
    if logged_in:
        expected = list(
            sorted(
                json.loads(
                    re.sub(
                        stage,
                        "test-***volatile***",
                        re.sub(r"-\w+\"", '-***volatile***"', cli_response.output),
                    )
                ),
                key=lambda x: x["search"]["min_size"],
            )
        )
    else:
        expected = cli_response.output
    snapshot.assert_match(expected)

    logger.info("Attempting to create a duplicate schedule...")
    cli_response = runner.invoke(
        cli,
        [
            "app",
            "scrape",
            "schedule",
            "create",
            transaction,
            post_codes,
            "--min-size",
            min_size,
            "--max-size",
            max_size,
            "--alias",
            "test",
        ],
    )
    assert cli_response.exit_code, cli_response.output
    snapshot.assert_match(cli_response.output)

    logger.info("Force-creating a scrape schedule...")
    cli_response = runner.invoke(
        cli,
        [
            "app",
            "scrape",
            "schedule",
            "create",
            transaction,
            post_codes,
            "--min-size",
            min_size,
            "--max-size",
            max_size,
            "--force",
            "--alias",
            "test",
        ],
    )
    assert cli_response.exit_code == (not logged_in), cli_response.output
    snapshot.assert_match(cli_response.output)

    logger.info("Deleting non-existent scrape schedules...")
    cli_response = runner.invoke(
        cli, ["app", "scrape", "schedule", "delete", "foo", "--alias", "test"],
    )
    assert cli_response.exit_code, cli_response.output
    snapshot.assert_match(cli_response.output)

    logger.info("Deleting scrape schedules...")
    if logged_in:
        cli_response = runner.invoke(
            cli,
            [
                "app",
                "scrape",
                "schedule",
                "delete",
                original_names[0] if logged_in else "foo",
                "--alias",
                "test",
            ],
        )
        assert cli_response.exit_code == (not logged_in), cli_response.output
        snapshot.assert_match(cli_response.output)
    cli_response = runner.invoke(
        cli, ["app", "scrape", "schedule", "clear", "--alias", "test"],
    )
    assert cli_response.exit_code == (not logged_in), cli_response.output
    snapshot.assert_match(cli_response.output)

    logger.info("Listing (once again empty) schedules...")
    cli_response = runner.invoke(
        cli, ["app", "scrape", "schedule", "list", "--alias", "test"],
    )
    assert cli_response.exit_code == (not logged_in), cli_response.output
    expected = empty_schedule_response
    actual = cli_response.output
    assert expected == actual
