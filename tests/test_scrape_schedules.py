from pogam.cli import cli
from click.testing import CliRunner
import pytest
from httmock import urlmatch, response, HTTMock
from requests.compat import urlparse
import os

here = os.path.dirname(__file__)


POGAM_API_HOST = "https://api.pogam-estate.local/"  # could be anything
netloc = urlparse(POGAM_API_HOST).netloc


# ------------------------------------------------------------------------------------ #
#                                       Fixtures                                       #
# ------------------------------------------------------------------------------------ #
@pytest.fixture
def endpoint_list():
    """Return a mock API response for a scrape schedules listing request."""
    f = os.path.join(here, "fixtures/scrape-schedules-api/list.json")
    with open(f) as f:
        resp = f.read()

    @urlmatch(netloc=netloc, path="/v1/scrape-schedules/", method="get")
    def mock_response(url, request):
        return response(200, resp)

    return {"mock_response": mock_response, "expected_response": resp}


# ------------------------------------------------------------------------------------ #
#                                         Tests                                        #
# ------------------------------------------------------------------------------------ #
class TestCli(object):
    def test_app_scrape_schedules_list(self, api_host, endpoint_list):
        runner = CliRunner()
        with HTTMock(endpoint_list["mock_response"]):
            result = runner.invoke(cli, ["app", "scrape-schedules", "list"])
        assert result.exit_code == 0
        assert endpoint_list["expected_response"] == result.output
