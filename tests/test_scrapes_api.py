import json
import logging
import os

import subprocess
import pytest
from click.testing import CliRunner
from httmock import HTTMock, response, urlmatch
from requests.compat import urlparse

from pogam.cli import cli

logger = logging.getLogger("pogam-tests")
here = os.path.dirname(__file__)
root_folder = os.path.abspath(os.path.join(here, ".."))
service_folder = os.path.join(root_folder, "app", "scrapes-api")

# ------------------------------------------------------------------------------------ #
#                                       Fixtures                                       #
# ------------------------------------------------------------------------------------ #
@pytest.fixture
def create_event():
    """HTTP event for the creation of a one-off scraping job."""
    f = os.path.join(here, "fixtures/scrapes-api/create-event.json")
    return str(f)


@pytest.fixture(params=[["rent", ["92130"]]])
def create_response(api_host, request):
    """Return a mock API response for a one-off scraping request."""
    f = os.path.join(here, "fixtures/scrapes-api/create-response.json")
    with open(f) as f:
        resp = f.read()[:-1]
    netloc = urlparse(api_host).netloc
    transaction, post_codes = request.param

    @urlmatch(netloc=netloc, path="/v1/scrapes", method="post")
    def mock_response(url, http_request):
        body = json.loads(http_request.body)
        if (
            body.get("search", {}).get("transaction") == transaction
            and body.get("search", {}).get("post_codes") == post_codes
        ):
            return response(200, resp)
        return response(500)

    return {
        "mock_response": mock_response,
        "expected_response": resp,
        "params": [transaction] + post_codes,
    }


@pytest.fixture
def run_event():
    """SNS event for running a scraing job."""
    f = os.path.join(here, "fixtures/scrapes-api/run-event.json")
    return str(f)


# ------------------------------------------------------------------------------------ #
#                                         Tests                                        #
# ------------------------------------------------------------------------------------ #
class TestCli(object):
    def test_create(self, api_host, create_response, snapshot):
        runner = CliRunner()
        with HTTMock(create_response["mock_response"]):
            result = runner.invoke(cli, ["app", "scrape"] + create_response["params"])
            assert result.exit_code == 0
            snapshot.assert_match(result.output)


class TestHandlers(object):
    def _handler_assert_match(
        self,
        handler_response: subprocess.CompletedProcess,
        stage,
        iferror_message: str,
        snapshot,
    ):
        iferror_message += f"\n{handler_response.stdout.decode('utf-8')}"
        assert handler_response.returncode == 0, iferror_message

    @pytest.mark.aws
    def test_scrape_run(self, stage, scrapes_api_service, run_event, snapshot):
        handler_response = subprocess.run(
            [
                "sls",
                "invoke",
                "--stage",
                stage,
                "--function",
                "run",
                "--path",
                run_event,
            ],
            cwd=service_folder,
            capture_output=True,
        )
        msg = "Running a one-off scraping job failed."
        self._handler_assert_match(handler_response, stage, msg, snapshot)
