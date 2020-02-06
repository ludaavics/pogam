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

# -------------------------------------- Events -------------------------------------- #
@pytest.fixture
def signup_event_template(user_name, user_email, user_password):
    """API gateway event for the signup handler."""

    def signup_event(
        *,
        name=user_name,
        email=user_email,
        password=user_password,
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
def resend_verification_event(user_email):
    """Return an API Gateway event for the resending a verification code handler."""
    with open(
        os.path.join(fixtures_folder, "resend-verification-event-template.json"), "r"
    ) as f:
        event = json.loads(f.read().replace("[EMAIL]", user_email))
    return event


@pytest.fixture
def confirm_signup_event(user_email):
    """Return an API Gateway event for the signup confirmation handler."""
    with open(
        os.path.join(fixtures_folder, "confirm-signup-event-template.json"), "r"
    ) as f:
        event = json.loads(
            f.read()
            .replace("[EMAIL]", user_email)
            .replace("[CONFIRMATION_CODE]", "1234")
        )
    return event


@pytest.fixture
def forgot_password_event(user_email):
    """Return an API Gateway event for forgotten password handler."""
    with open(
        os.path.join(fixtures_folder, "forgot-password-event-template.json"), "r"
    ) as f:
        event = json.loads(f.read().replace("[EMAIL]", user_email))
    return event


# --------------------------------------- Users -------------------------------------- #
@pytest.fixture
def user_unconfirmed(
    user_pool_id, user_pool_client_id, user_name, user_email, user_password
):
    cognito = boto3.client("cognito-idp")
    cognito.sign_up(
        ClientId=user_pool_client_id,
        Username=user_email,
        Password=user_password,
        UserAttributes=[
            {"Name": "name", "Value": user_name},
            {"Name": "email", "Value": user_email},
        ],
        ValidationData=[
            {"Name": "email", "Value": user_email},
            {"Name": "custom:username", "Value": user_email},
        ],
    )
    yield
    cognito.admin_delete_user(UserPoolId=user_pool_id, Username=user_email)


@pytest.fixture
def cleanup_users(user_pool_id):
    yield
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
def sls_invoke(stage, function, data, folder=service_folder):
    return subprocess.run(
        [
            "sls",
            "invoke",
            "--stage",
            stage,
            "--function",
            function,
            "--data",
            json.dumps(data),
        ],
        cwd=folder,
        capture_output=True,
    )


def handler_assert_match(
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


# -------------------------------------- Signup -------------------------------------- #
@pytest.mark.aws
@pytest.mark.parametrize(
    "password", ["hi", "H3l!o W", "h3llo world!", "H3LLO WORLD!", "H3llo World"],
)
def test_signup_invalid_password(
    stage, users_api_service, signup_event_template, cleanup_users, password, snapshot,
):
    signup_event_invalid_password = signup_event_template(password=password)
    handler_response = sls_invoke(stage, "signup", signup_event_invalid_password)
    msg = (
        f"Signup with invalid password failed:\n"
        f"{handler_response.stdout.decode('utf-8')}"
    )
    expected_status_code = 400
    handler_assert_match(handler_response, stage, msg, expected_status_code, snapshot)


@pytest.mark.aws
def test_signup_invalid_invitation_code(
    stage, users_api_service, signup_event_template, snapshot, cleanup_users
):
    signup_event_invalid_invitation_code = signup_event_template(
        invitation_code="invalid code"
    )
    handler_response = sls_invoke(stage, "signup", signup_event_invalid_invitation_code)
    msg = (
        f"Signup with invalid invitation code failed:\n"
        f"{handler_response.stdout.decode('utf-8')}"
    )
    expected_status_code = 400
    handler_assert_match(handler_response, stage, msg, expected_status_code, snapshot)


@pytest.mark.aws
def test_signup(
    stage, cleanup_users, users_api_service, signup_event_template, snapshot
):
    signup_event = signup_event_template(password="H3llo World!")
    handler_response = sls_invoke(stage, "signup", signup_event)
    msg = f"Signup failed:\n" f"{handler_response.stdout.decode('utf-8')}"
    expected_status_code = 200
    handler_assert_match(handler_response, stage, msg, expected_status_code, snapshot)


# ----------------------------- Resend Verification Code ----------------------------- #
@pytest.mark.aws
def test_resend_verification_code_invalid_user(
    stage, users_api_service, resend_verification_event, snapshot
):
    handler_response = sls_invoke(
        stage, "resend-verification", resend_verification_event
    )
    msg = (
        f"Resending verification code of invalid user failed:\n"
        f"{handler_response.stdout.decode('utf-8')}"
    )
    expected_status_code = 400
    handler_assert_match(handler_response, stage, msg, expected_status_code, snapshot)


@pytest.mark.aws
def test_resend_verification_code_already_confirmed(
    stage, user, users_api_service, resend_verification_event, snapshot
):
    handler_response = sls_invoke(
        stage, "resend-verification", resend_verification_event
    )
    msg = (
        f"Resending verification code of already confirmed user failed:\n"
        f"{handler_response.stdout.decode('utf-8')}"
    )
    expected_status_code = 200
    handler_assert_match(handler_response, stage, msg, expected_status_code, snapshot)


@pytest.mark.aws
def test_resend_verification_code(
    stage, user_unconfirmed, users_api_service, resend_verification_event, snapshot
):
    handler_response = sls_invoke(
        stage, "resend-verification", resend_verification_event
    )
    msg = (
        f"Resending verification code failed:\n"
        f"{handler_response.stdout.decode('utf-8')}"
    )
    expected_status_code = 200
    handler_assert_match(handler_response, stage, msg, expected_status_code, snapshot)


# ---------------------------------- Confirm Signup ---------------------------------- #
@pytest.mark.aws
def test_confirm_signup_invalid_user(
    stage, users_api_service, confirm_signup_event, snapshot
):
    handler_response = sls_invoke(stage, "confirm-signup", confirm_signup_event)
    msg = (
        f"Confirm signup of invalid user failed:\n"
        f"{handler_response.stdout.decode('utf-8')}"
    )
    expected_status_code = 400
    handler_assert_match(handler_response, stage, msg, expected_status_code, snapshot)


@pytest.mark.aws
def test_confirm_signup_already_confirmed(
    stage, user, users_api_service, confirm_signup_event, snapshot
):
    handler_response = sls_invoke(stage, "confirm-signup", confirm_signup_event)
    msg = (
        f"Confirm signup of already confirmed user failed:\n"
        f"{handler_response.stdout.decode('utf-8')}"
    )
    expected_status_code = 200
    handler_assert_match(handler_response, stage, msg, expected_status_code, snapshot)


@pytest.mark.aws
@pytest.mark.xfail
def test_confirm_signup(self):
    # unclear how to mock the reception of email code.
    assert False


# ---------------------------------- Forgot Password --------------------------------- #
@pytest.mark.aws
def test_forgot_password_invalid_user(
    stage, users_api_service, forgot_password_event, snapshot
):
    handler_response = sls_invoke(stage, "forgot-password", forgot_password_event)
    msg = (
        f"Forgot password of invalid user failed:\n"
        f"{handler_response.stdout.decode('utf-8')}"
    )
    expected_status_code = 400
    handler_assert_match(handler_response, stage, msg, expected_status_code, snapshot)


@pytest.mark.aws
def test_forgot_password_unconfirmed_user(
    stage, user_unconfirmed, users_api_service, forgot_password_event, snapshot
):
    handler_response = sls_invoke(stage, "forgot-password", forgot_password_event)
    msg = (
        f"Forgot password of unconfirmed user failed:\n"
        f"{handler_response.stdout.decode('utf-8')}"
    )
    expected_status_code = 400
    handler_assert_match(handler_response, stage, msg, expected_status_code, snapshot)


@pytest.mark.aws
def test_forgot_password(
    stage, user, users_api_service, forgot_password_event, snapshot
):
    handler_response = sls_invoke(stage, "forgot-password", forgot_password_event)
    msg = f"Forgot password failed:\n" f"{handler_response.stdout.decode('utf-8')}"
    expected_status_code = 200
    handler_assert_match(handler_response, stage, msg, expected_status_code, snapshot)
