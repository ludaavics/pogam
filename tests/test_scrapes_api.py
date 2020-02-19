import logging
import re

import pytest
from click.testing import CliRunner

from pogam.cli import cli

logger = logging.getLogger("pogam-tests")


@pytest.mark.aws
@pytest.mark.parametrize(
    "transaction, post_codes, min_size, max_size, logged_in",
    [("rent", "92130", "29", "31", True), ("rent", "92130", "29", "31", False)],
)
def test_cli_app_scrape_create(
    cli_login,
    cli_temporary_logout,
    scrapes_api_service,
    transaction,
    post_codes,
    min_size,
    max_size,
    logged_in,
    snapshot,
):
    if not logged_in:
        cli_temporary_logout()
    runner = CliRunner()
    cli_response = runner.invoke(
        cli,
        [
            "app",
            "scrape",
            "run",
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
    assert cli_response.exit_code == (not logged_in), cli_response.output
    expected = re.sub(
        r"\(message id: \S+\)",
        "(message id: ***volatile-value***)",
        cli_response.output,
    )
    snapshot.assert_match(expected)
