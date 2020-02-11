import json
import logging
import os
import re

import pytest
from click.testing import CliRunner

from pogam.cli import cli

logger = logging.getLogger("pogam-tests")
here = os.path.dirname(__file__)
root_folder = os.path.abspath(os.path.join(here, ".."))
service_folder = os.path.join(root_folder, "app", "scrapes-api")


# ------------------------------------------------------------------------------------ #
#                                         Tests                                        #
# ------------------------------------------------------------------------------------ #
@pytest.mark.aws
@pytest.mark.parametrize(
    "transaction, post_codes, min_size, max_size", [("rent", "92130", "29", "31")]
)
def test_cli_app_scrape_create(
    stage, scrapes_api_service, transaction, post_codes, min_size, max_size, snapshot
):
    runner = CliRunner()
    cli_response = runner.invoke(
        cli,
        [
            "app",
            "scrape",
            "create",
            transaction,
            post_codes,
            "--min-size",
            min_size,
            "--max-size",
            max_size,
        ],
    )
    assert cli_response.exit_code == 0
    expected = re.sub(
        r"\(message id: \S+\)",
        "(message id: ***volatile-value***)",
        cli_response.output,
    )
    snapshot.assert_match(expected)
