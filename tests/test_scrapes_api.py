import json
import logging
import os

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
    """API Gateway event for the creation of a scrape"""
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
