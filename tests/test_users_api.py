import json
import logging
import os
import subprocess

import boto3
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
        email="test.user@pogam-estate.com",
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


@pytest.fixture
def cleanup_users(stage):
    yield
    cloudformation = boto3.client("cloudformation")
    exports = cloudformation.list_exports()["Exports"]
    user_pool_id = [
        export for export in exports if export["Name"] == f"{stage}UserPoolId"
    ]
    assert len(user_pool_id) == 1
    user_pool_id = user_pool_id[0]["Value"]

    cognito = boto3.client("cognito-idp")
    responses = []
    has_next_page = True
    while has_next_page:
        page = cognito.list_users(UserPoolId=user_pool_id, Limit=60)
        responses += [
            cognito.admin_delete_user(
                UserPoolId=user_pool_id, Username=user["Username"]
            )
            for user in page["Users"]
        ]
        has_next_page = "PaginationToken" in page


# ------------------------------------------------------------------------------------ #
#                                         Tests                                        #
# ------------------------------------------------------------------------------------ #
class TestHandlers(object):
    def _handler_assert_match(
        self,
        handler_response: subprocess.CompletedProcess,
        stage,
        iferror_message: str,
        status_code,
        snapshot,
    ):
        logger.debug(handler_response.stdout.decode("utf-8"))
        assert handler_response.returncode == 0, iferror_message
        api_response = json.loads(
            handler_response.stdout.decode("utf-8").replace(stage, "test")
        )
        api_response["body"] = json.loads(api_response.get("body"))
        assert api_response["statusCode"] == status_code
        snapshot.assert_match(api_response)

    @pytest.mark.aws
    @pytest.mark.parametrize(
        "password", ["hi", "H3l!o W", "h3llo world!", "H3LLO WORLD!", "H3llo World"],
    )
    def test_password_validation(
        self,
        stage,
        users_api_service,
        signup_event_template,
        cleanup_users,
        password,
        snapshot,
    ):
        signup_event_invalid_password = signup_event_template(password=password)
        handler_response = subprocess.run(
            [
                "sls",
                "invoke",
                "--stage",
                stage,
                "--function",
                "signup",
                "--data",
                json.dumps(signup_event_invalid_password),
            ],
            cwd=service_folder,
            capture_output=True,
        )
        msg = (
            f"Signup with invalid password failed:\n"
            f"{handler_response.stderr.decode('utf-8')}"
        )
        expected_status_code = 400
        self._handler_assert_match(
            handler_response, stage, msg, expected_status_code, snapshot
        )

    @pytest.mark.aws
    def test_invalid_invitation_code(
        self, stage, users_api_service, signup_event_template, snapshot, cleanup_users
    ):
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
        expected_status_code = 400
        self._handler_assert_match(
            handler_response, stage, msg, expected_status_code, snapshot
        )
