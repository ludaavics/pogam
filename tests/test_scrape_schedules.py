import json
import os
import subprocess

import pytest
from click.testing import CliRunner
from httmock import HTTMock, response, urlmatch
from requests.compat import urlparse

from pogam.cli import cli

here = os.path.dirname(__file__)
root_folder = os.path.abspath(os.path.join(here, ".."))
service_folder = os.path.join(root_folder, "app", "scrape-schedules-api")


# ------------------------------------------------------------------------------------ #
#                                       Fixtures                                       #
# ------------------------------------------------------------------------------------ #
@pytest.fixture
def list_response(api_host):
    """Return a mock API response for a scrape schedules listing request."""
    f = os.path.join(here, "fixtures/scrape-schedules-api/list-response.json")
    with open(f) as f:
        resp = f.read()[:-1]
    netloc = urlparse(api_host).netloc

    @urlmatch(netloc=netloc, path="/v1/scrape-schedules", method="get")
    def mock_response(url, request):
        return response(200, resp)

    return {"mock_response": mock_response, "expected_response": resp}


@pytest.fixture
def list_event():
    """Return an API Gateway event for the list handler."""
    f = os.path.join(here, "fixtures/scrape-schedules-api/list-event.json")
    return str(f)
    with open(f) as f:
        event = f.read()
    return event


# ------------------------------------------------------------------------------------ #
#                                         Tests                                        #
# ------------------------------------------------------------------------------------ #
class TestCli(object):
    def test_list(self, api_host, list_response):
        """CLI command for listing scheduled scrapes."""
        runner = CliRunner()
        with HTTMock(list_response["mock_response"]):
            result = runner.invoke(cli, ["app", "scrape-schedules", "list"])
        assert result.exit_code == 0
        expected = json.loads(list_response["expected_response"])
        actual = json.loads(result.output)
        assert expected == actual


class TestHandlers(object):
    @pytest.mark.aws
    def test_crud(self, stage, scrape_schedules_api_service, list_event, snapshot):
        """Scrape Schedules CRUD handlers"""
        # list (empty) schedules
        result = subprocess.run(
            [
                "sls",
                "invoke",
                "--stage",
                stage,
                "--function",
                "list",
                "--path",
                list_event,
            ],
            cwd=service_folder,
            capture_output=True,
        )

        assert result.returncode == 0
        actual = json.loads(result.stdout)
        snapshot.assert_match(actual)
