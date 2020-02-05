import logging
import os
import subprocess
import uuid
import contextlib

import boto3
import pytest

here = os.path.dirname(__file__)
root_folder = os.path.abspath(os.path.join(here, ".."))
logger = logging.getLogger("pogam-test")

POGAM_API_HOST = "https://api.pogam-estate.local/"  # could be anything


# ------------------------------------------------------------------------------------ #
#                          Command Line Options Configuration                          #
# ------------------------------------------------------------------------------------ #
def pytest_addoption(parser):
    parser.addoption(
        "--deploy-app",
        action="store_true",
        default=False,
        help="Deploy the app and run tests that rely on a deployed app.",
    )

    parser.addoption(
        "--keep-app",
        action="store_true",
        default=False,
        help="Keep the app deployed after tests execution.",
    )

    parser.addoption(
        "--stage",
        action="store",
        default=None,
        help="Deploy app to a specific stage. Ignored if --deploy-app is False.",
    )


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "aws: mark test as requiring the deployment of the app's services"
    )


def pytest_collection_modifyitems(config, items):
    if config.getoption("--deploy-app"):
        return
    skip_aws = pytest.mark.skip(
        reason="Requires deployed services. Use --deploy-app option to run."
    )
    for item in items:
        if "aws" in item.keywords:
            item.add_marker(skip_aws)


# ------------------------------------------------------------------------------------ #
#                                        Fixtures                                      #
# ------------------------------------------------------------------------------------ #
@pytest.fixture
def api_host():
    original_host = os.getenv("POGAM_API_HOST")
    test_host = POGAM_API_HOST
    if test_host is None:
        msg = "Missing 'POGAM_API_HOST' environment variable."
        raise ValueError(msg)
    os.environ["POGAM_API_HOST"] = test_host
    yield test_host
    if original_host:
        os.environ["POGAM_API_HOST"] = original_host


# ----------------------------------- AWS services ----------------------------------- #
@pytest.fixture(scope="session")
def stage(request):
    return (
        request.config.getoption("--stage") or f"test-{str(uuid.uuid4()).split('-')[0]}"
    )


@contextlib.contextmanager
def deploy(request, service, stage):
    logger.info(f"Deploying {service} service to stage {stage}...")
    folder = os.path.join(root_folder, "app", service)
    subprocess.run(["sls", "deploy", "--stage", stage], cwd=folder)
    yield
    if request.config.getoption("--keep-app"):
        return
    logger.info(f"Tearing down {service} service from stage {stage}...")
    subprocess.run(["sls", "remove", "--stage", stage], cwd=folder)


@pytest.fixture(scope="session")
def shared_resources_service(request, stage):
    with contextlib.ExitStack() as stack:
        yield stack.enter_context(deploy(request, "shared-resources", stage))


@pytest.fixture(scope="session")
def users_api_service(request, shared_resources_service, stage):
    with contextlib.ExitStack() as stack:
        ssm = boto3.client("ssm")
        ssm.put_parameter(
            Name=f"/pogam/{stage}/users/invitation-code",
            Description="Invitation code for user sign up.",
            Value="test invitation code",
            Type="String",
            Tier="Standard",
            Overwrite=True,
        )
        yield stack.enter_context(deploy(request, "users-api", stage))
        ssm.delete_parameter(Name=f"/pogam/{stage}/users/invitation-code",)


@pytest.fixture(scope="session")
def scrapes_api_service(request, shared_resources_service, stage):
    with contextlib.ExitStack() as stack:
        yield stack.enter_context(deploy(request, "scrapes-api", stage))


@pytest.fixture
def scrape_schedules_api_service(request, scrapes_api_service, stage):
    with contextlib.ExitStack() as stack:
        yield stack.enter_context(deploy(request, "scrape-schedules-api", stage))


# ------------------------------ AWS exported resources ------------------------------ #
@pytest.fixture(scope="session")
def user_pool_id(stage, shared_resources_service):
    cloudformation = boto3.client("cloudformation")
    exports = cloudformation.list_exports()["Exports"]
    user_pools = [
        export for export in exports if export["Name"] == f"{stage}UserPoolId"
    ]
    assert len(user_pools) == 1
    return user_pools[0]["Value"]


@pytest.fixture(scope="session")
def user_pool_client_id(stage, shared_resources_service):
    cloudformation = boto3.client("cloudformation")
    exports = cloudformation.list_exports()["Exports"]
    user_pool_clients = [
        export for export in exports if export["Name"] == f"{stage}UserPoolClientId"
    ]
    assert len(user_pool_clients) == 1
    return user_pool_clients[0]["Value"]


# ------------------------------------- Test user ------------------------------------ #
@pytest.fixture()
def user_name():
    return "Test User"


@pytest.fixture()
def user_email():
    return "test.user@pogam-estate.com"


@pytest.fixture()
def user_password():
    return "H3llo World!"


@pytest.fixture()
def user(
    stage, user_pool_id, user_pool_client_id, user_name, user_email, user_password
):
    cognito = boto3.client("cognito-idp")
    try:
        cognito.admin_delete_user(UserPoolId=user_pool_id, Username=user_email)
    except cognito.exceptions.UserNotFoundException:
        pass

    # create the user, with a temporary password
    temporary_password = "Temp0Rary !"
    cognito.admin_create_user(
        UserPoolId=user_pool_id,
        Username=user_email,
        UserAttributes=[
            {"Name": "name", "Value": user_name},
            {"Name": "email", "Value": user_email},
            {"Name": "email_verified", "Value": "True"},
        ],
        TemporaryPassword=temporary_password,
    )

    # log in and change the password
    auth_challenge = cognito.admin_initiate_auth(
        UserPoolId=user_pool_id,
        ClientId=user_pool_client_id,
        AuthFlow="ADMIN_USER_PASSWORD_AUTH",
        AuthParameters={"USERNAME": user_email, "PASSWORD": temporary_password},
    )
    cognito.admin_respond_to_auth_challenge(
        UserPoolId=user_pool_id,
        ClientId=user_pool_client_id,
        ChallengeName="NEW_PASSWORD_REQUIRED",
        ChallengeResponses={"USERNAME": user_email, "NEW_PASSWORD": user_password},
        Session=auth_challenge["Session"],
    )
    yield
    cognito.admin_delete_user(UserPoolId=user_pool_id, Username=user_email)
