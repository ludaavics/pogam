import logging
import os
import json
import re

import pytest
from click.testing import CliRunner

from pogam.cli import cli

logger = logging.getLogger("pogam-tests")
here = os.path.dirname(__file__)
root_folder = os.path.abspath(os.path.join(here, ".."))
service_folder = os.path.join(root_folder, "app", "scrapes-api")

# ------------------------------------------------------------------------------------ #
#                                       Fixtures                                       #
# ------------------------------------------------------------------------------------ #
@pytest.fixture(scope="session")
def cli_login(api_host, user, user_email, user_password):
    runner = CliRunner()
    cli_response = runner.invoke(
        cli,
        [
            "app",
            "login",
            "--email",
            user_email,
            "--password",
            user_password,
            "--alias",
            "test",
        ],
    )
    assert cli_response.exit_code == 0, cli_response.output
    yield
    runner.invoke(cli, ["app", "logout", "--alias", "test"])


@pytest.fixture
def cli_temporary_logout():
    folder = os.path.expanduser("~/.pogam/")
    credentials_path = os.path.join(folder, "credentials")
    try:
        with open(credentials_path, "r") as f:
            all_credentials = json.load(f)
    except FileNotFoundError:
        all_credentials = {}

    def _logout(alias="test"):
        all_credentials_temp = {
            k: all_credentials[k] for k in all_credentials if k != alias
        }
        with open(credentials_path, "w") as f:
            json.dump(all_credentials_temp, f)

    yield _logout
    with open(credentials_path, "w") as f:
        json.dump(all_credentials, f)


# ------------------------------------------------------------------------------------ #
#                                         Tests                                        #
# ------------------------------------------------------------------------------------ #
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
    assert cli_response.exit_code == (not logged_in), cli_response.output
    expected = re.sub(
        r"\(message id: \S+\)",
        "(message id: ***volatile-value***)",
        cli_response.output,
    )
    snapshot.assert_match(expected)
