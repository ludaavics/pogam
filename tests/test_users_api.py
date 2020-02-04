import json
import logging
import os
import subprocess

import pytest

logger = logging.getLogger("pogam-tests")
here = os.path.dirname(__file__)
root_folder = os.path.abspath(os.path.join(here, ".."))
fixtures_folder = os.path.join(root_folder, "tests", "fixtures", "users-api")
service_folder = os.path.join(root_folder, "app", "users-api")

# ------------------------------------------------------------------------------------ #
#                                       Fixtures                                       #
# ------------------------------------------------------------------------------------ #
@pytest.fixture
def signup_event_template():
    """API gateway event for the signup handler."""

    def signup_event(
        *,
        name="Test User",
        email="test.user@gmail.com",
        password="H3llo World!",
        invitation_code="test invitation code",
    ):
        with open(
            os.path.join(fixtures_folder, "signup-event-template.json"), "r",
        ) as f:
            event = json.loads(
                f.read()
                .replace("[NAME]", name)
                .replace("[EMAIL]", email)
                .replace("[PASSWORD]", password)
                .replace("[INVITATION_CODE]", invitation_code)
            )
        return event

    return signup_event


# ------------------------------------------------------------------------------------ #
#                                         Tests                                        #
# ------------------------------------------------------------------------------------ #
class TestHandlers(object):
    def _handler_assert_match(
        self,
        handler_response: subprocess.CompletedProcess,
        stage,
        iferror_message: str,
        snapshot,
    ):
        logger.debug(handler_response.stdout.decode("utf-8"))
        assert handler_response.returncode == 0, iferror_message
        api_response = json.loads(
            handler_response.stdout.decode("utf-8").replace(stage, "test")
        )
        api_response["body"] = json.loads(api_response.get("body"))
        snapshot.assert_match(api_response)

    @pytest.mark.aws
    def test_user_creation(
        self, stage, users_api_service, signup_event_template, snapshot
    ):
        logger.info("Attempting to sign up with invalid invitation code...")
        signup_event_invalid_invitation_code = signup_event_template(
            invitation_code="invalid code"
        )
        handler_response = subprocess.run(
            [
                "sls",
                "invoke",
                "--stage",
                stage,
                "--function",
                "signup",
                "--data",
                json.dumps(signup_event_invalid_invitation_code),
            ],
            cwd=service_folder,
            capture_output=True,
        )
        msg = (
            f"Signup with invalid invitation code failed:\n"
            f"{handler_response.stderr.decode('utf-8')}"
        )
        self._handler_assert_match(handler_response, stage, msg, snapshot)

        logger.info("Attempting to sign up with a short password...")
        signup_event_short_password = signup_event_template(password="hi")
        handler_response = subprocess.run(
            [
                "sls",
                "invoke",
                "--stage",
                stage,
                "--function",
                "signup",
                "--data",
                json.dumps(signup_event_short_password),
            ],
            cwd=service_folder,
            capture_output=True,
        )
        msg = (
            f"Signup with short password failed:\n"
            f"{handler_response.stderr.decode('utf-8')}"
        )
        self._handler_assert_match(handler_response, stage, msg, snapshot)

        logger.info("Attempting to sign up with a weak password...")
        signup_event_weak_password = signup_event_template(password="hello world")
        handler_response = subprocess.run(
            [
                "sls",
                "invoke",
                "--stage",
                stage,
                "--function",
                "signup",
                "--data",
                json.dumps(signup_event_weak_password),
            ],
            cwd=service_folder,
            capture_output=True,
        )
        msg = (
            f"Signup with weak password failed:\n"
            f"{handler_response.stderr.decode('utf-8')}"
        )
        self._handler_assert_match(handler_response, stage, msg, snapshot)
