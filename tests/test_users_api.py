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
def resend_verification_event_template(user_email):
    """API Gateway event for resending a verification code."""

    def resend_verification_event(*, email=user_email):
        with open(
            os.path.join(fixtures_folder, "resend-verification-event-template.json"),
            "r",
        ) as f:
            event = json.loads(f.read().replace("[EMAIL]", email))
        return event

    return resend_verification_event


@pytest.fixture
def confirm_signup_event_template(user_email):
    """API Gateway event for the signup confirmation."""

    def confirm_signup_event(email=user_email, verification_code="1234"):
        with open(
            os.path.join(fixtures_folder, "confirm-signup-event-template.json"), "r"
        ) as f:
            event = json.loads(
                f.read()
                .replace("[EMAIL]", email)
                .replace("[VERIFICATION_CODE]", verification_code)
            )
        return event

    return confirm_signup_event


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
def user_email_unconfirmed():
    return "test.user.unconfirmed@pogam-estate.com"


@pytest.fixture
def user_email_not_found():
    return "test.user.foo@pogam-estate.com"


@pytest.fixture
def user_unconfirmed(
    user_pool_id, user_pool_client_id, user_name, user_email_unconfirmed, user_password
):
    cognito = boto3.client("cognito-idp")
    cognito.sign_up(
        ClientId=user_pool_client_id,
        Username=user_email_unconfirmed,
        Password=user_password,
        UserAttributes=[
            {"Name": "name", "Value": user_name},
            {"Name": "email", "Value": user_email_unconfirmed},
        ],
        ValidationData=[
            {"Name": "email", "Value": user_email_unconfirmed},
            {"Name": "custom:username", "Value": user_email_unconfirmed},
        ],
    )
    yield
    cognito.admin_delete_user(UserPoolId=user_pool_id, Username=user_email_unconfirmed)


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
    assert api_response["statusCode"] == status_code, api_response
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
@pytest.mark.parametrize(
    "user_status, status_code",
    [("not_found", 400), ("unconfirmed", 200), ("confirmed", 200)],
)
def test_resend_verification_code(
    stage,
    user_email_not_found,
    user_email_unconfirmed,
    user_email,
    user,
    user_unconfirmed,
    users_api_service,
    resend_verification_event_template,
    user_status,
    status_code,
    snapshot,
):
    email = {
        "not_found": user_email_not_found,
        "unconfirmed": user_email_unconfirmed,
        "confirmed": user_email,
    }[user_status]
    resend_verification_event = resend_verification_event_template(email=email)
    handler_response = sls_invoke(
        stage, "resend-verification", resend_verification_event
    )
    msg = (
        f"Resending verification code failed:\n"
        f"{handler_response.stdout.decode('utf-8')}"
    )
    handler_assert_match(handler_response, stage, msg, status_code, snapshot)


# ---------------------------------- Confirm Signup ---------------------------------- #
@pytest.mark.aws
@pytest.mark.parametrize(
    "user_status, status_code",
    [("not_found", 400), ("unconfirmed", 400), ("confirmed", 200)],
)
def test_confirm_signup(
    stage,
    user_email_not_found,
    user_email_unconfirmed,
    user_email,
    user,
    user_unconfirmed,
    users_api_service,
    confirm_signup_event_template,
    user_status,
    status_code,
    snapshot,
):
    if user_status == "confirmed":
        msg = "Unclear how to mock the reception of email verification code."
        pytest.xfail(msg)

    email = {
        "not_found": user_email_not_found,
        "unconfirmed": user_email_unconfirmed,
        "confirmed": user_email,
    }[user_status]

    confirm_signup_event = confirm_signup_event_template(email=email)
    handler_response = sls_invoke(stage, "confirm-signup", confirm_signup_event)
    msg = f"Confirm signup failed:\n" f"{handler_response.stdout.decode('utf-8')}"
    handler_assert_match(handler_response, stage, msg, status_code, snapshot)


@pytest.mark.aws
def test_confirm_signup_invalid_verification_code(
    stage,
    user_email_unconfirmed,
    user_unconfirmed,
    users_api_service,
    confirm_signup_event_template,
    snapshot,
):
    confirm_signup_event = confirm_signup_event_template(email=user_email_unconfirmed)
    handler_response = sls_invoke(stage, "confirm-signup", confirm_signup_event)
    msg = (
        f"Confirm signup with invalid verification code failed:\n"
        f"{handler_response.stdout.decode('utf-8')}"
    )
    expected_status_code = 400
    handler_assert_match(handler_response, stage, msg, expected_status_code, snapshot)


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
