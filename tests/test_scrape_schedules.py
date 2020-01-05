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


@pytest.fixture
def create_events():
    """Return an API Gateway event for the create handler."""
    return [
        str(
            os.path.join(here, f"fixtures/scrape-schedules-api/create-event-{num}.json")
        )
        for num in ["01", "02"]
    ]


@pytest.fixture
def create_force_event():
    """Return an API Gateway event for the list handler."""
    f = os.path.join(here, "fixtures/scrape-schedules-api/create-force-event.json")
    return str(f)


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
    def _handler_assert_match(
        self,
        handler_response: subprocess.CompletedProcess,
        stage,
        iferror_message: str,
        snapshot,
    ):
        assert handler_response.returncode == 0, iferror_message
        api_response = json.loads(
            handler_response.stdout.decode("utf-8").replace(stage, "test")
        )
        api_response["body"] = json.loads(api_response.get("body"))
        snapshot.assert_match(api_response)

    def _handler_remove_uuid_from_schedule_name(
        self, handler_response: subprocess.CompletedProcess
    ):
        """Remove UUID from schedule names in place and returns the original names."""
        api_response = json.loads(handler_response.stdout)
        api_response["body"] = json.loads(api_response["body"])
        original_names = [None] * len(api_response["body"]["data"])
        for i, schedule in enumerate(api_response["body"]["data"]):
            original_names[i] = schedule["name"]
            schedule["name"] = "-".join(schedule["name"].split("-")[:-1])
        api_response["body"] = json.dumps(api_response["body"], indent=2)
        handler_response.stdout = json.dumps(api_response).encode("utf-8")
        return original_names

    @pytest.mark.aws
    def test_crud(
        self,
        stage,
        scrape_schedules_api_service,
        create_events,
        create_force_event,
        list_event,
        snapshot,
    ):
        """Scrape Schedules CRUD handlers"""
        logger.info("Listing (empty) schedules...")
        handler_response = subprocess.run(
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
        msg = (
            f"Listing empty scrape schedule failed:\n"
            f"{handler_response.stderr.decode('utf-8')}"
        )
        self._handler_assert_match(handler_response, stage, msg, snapshot)

        logger.info("Adding new scrape schedules...")
        for i, create_event in enumerate(create_events):
            handler_response = subprocess.run(
                [
                    "sls",
                    "invoke",
                    "--stage",
                    stage,
                    "--function",
                    "create",
                    "--path",
                    create_event,
                ],
                cwd=service_folder,
                capture_output=True,
            )
            msg = (
                f"Creating scrape schedule #{i} failed:\n"
                f"{handler_response.stderr.decode('utf-8')}"
            )
            self._handler_remove_uuid_from_schedule_name(handler_response)
            self._handler_assert_match(handler_response, stage, msg, snapshot)

        logger.info("Listing the new schedule...")
        handler_response = subprocess.run(
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
        original_names = self._handler_remove_uuid_from_schedule_name(handler_response)
        msg = (
            f"Listing scrape schedule failed:\n"
            f"{handler_response.stderr.decode('utf-8')}"
        )
        self._handler_assert_match(handler_response, stage, msg, snapshot)

        logger.info("Attempting to create a duplicate schedule...")
        handler_response = subprocess.run(
            [
                "sls",
                "invoke",
                "--stage",
                stage,
                "--function",
                "create",
                "--path",
                create_event,
            ],
            cwd=service_folder,
            capture_output=True,
        )
        msg = (
            f"Creating a duplicate scrape schedule failed:\n"
            f"{handler_response.stderr.decode('utf-8')}"
        )
        self._handler_assert_match(handler_response, stage, msg, snapshot)

        logger.info("Force-creating a scrape schedule...")
        handler_response = subprocess.run(
            [
                "sls",
                "invoke",
                "--stage",
                stage,
                "--function",
                "create",
                "--path",
                create_force_event,
            ],
            cwd=service_folder,
            capture_output=True,
        )
        msg = (
            f"Force-creating a scrape schedule failed:\n"
            f"{handler_response.stderr.decode('utf-8')}"
        )
        self._handler_remove_uuid_from_schedule_name(handler_response)
        self._handler_assert_match(handler_response, stage, msg, snapshot)

        logger.info("Deleting scrape schedules...")
        for name in original_names:
            handler_response = subprocess.run(
                [
                    "sls",
                    "invoke",
                    "--stage",
                    stage,
                    "--function",
                    "create",
                    "--path",
                    create_force_event,
                ],
                cwd=service_folder,
                capture_output=True,
            )
            msg = (
                f"Deleting scrape schedule #{i} has failed:\n"
                f"{handler_response.stderr.decode('utf-8')}"
            )
            self._handler_remove_uuid_from_schedule_name(handler_response)
            self._handler_assert_match(handler_response, stage, msg, snapshot)
