import contextlib
import json
import logging
import os
import subprocess
import time
import uuid

import boto3
import pytest
from click.testing import CliRunner

from pogam.cli import cli

here = os.path.dirname(__file__)
root_folder = os.path.abspath(os.path.join(here, ".."))
logger = logging.getLogger("pogam-test")


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
        logger.info(f"Deleting photos downloaded in stage {stage}...")
        if request.config.getoption("--keep-app"):
            return
        cloudformation = boto3.client("cloudformation")
        exports = cloudformation.list_exports()["Exports"]
        resources = [
            resource
            for resource in exports
            if resource["Name"] == f"{stage}PhotosBucketName"
        ]
        assert len(resources) == 1
        bucket_name = resources[0]["Value"]
        boto3.resource("s3").Bucket(bucket_name).objects.all().delete()


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


@pytest.fixture(scope="session")
def scrape_schedules_api_service(request, scrapes_api_service, stage):
    with contextlib.ExitStack() as stack:
        yield stack.enter_context(deploy(request, "scrape-schedules-api", stage))


# ------------------------------ AWS exported resources ------------------------------ #
@pytest.fixture(scope="session")
def api_host(stage, shared_resources_service):
    original_host = os.getenv("POGAM_API_HOST")

    cloudformation = boto3.client("cloudformation")
    exports = cloudformation.list_exports()["Exports"]
    resources = [
        resource
        for resource in exports
        if resource["Name"] == f"{stage}ApiGatewayRestApiId"
    ]
    assert len(resources) == 1
    rest_api_id = resources[0]["Value"]
    region = cloudformation.meta.region_name
    test_host = f"https://{rest_api_id}.execute-api.{region}.amazonaws.com/{stage}/"
    os.environ["POGAM_API_HOST"] = test_host
    yield test_host
    if original_host:
        os.environ["POGAM_API_HOST"] = original_host


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
@pytest.fixture(scope="session")
def user_name():
    return "Test User"


@pytest.fixture(scope="session")
def user_email():
    return "test.user@pogam-estate.com"


@pytest.fixture(scope="session")
def user_password():
    return "H3llo World!"


@pytest.fixture(scope="session")
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
    time.sleep(0.5)
    yield
    cognito.admin_delete_user(UserPoolId=user_pool_id, Username=user_email)
    time.sleep(0.5)


@pytest.fixture(scope="session")
def api_token(user, user_pool_id, user_pool_client_id, user_email, user_password):
    cognito = boto3.client("cognito-idp")
    auth = cognito.admin_initiate_auth(
        UserPoolId=user_pool_id,
        ClientId=user_pool_client_id,
        AuthFlow="ADMIN_USER_PASSWORD_AUTH",
        AuthParameters={"USERNAME": user_email, "PASSWORD": user_password},
        ClientMetadata={"username": user_email, "password": user_password},
    )
    return auth["AuthenticationResult"]["IdToken"]


# ---------------------------------------- CLI --------------------------------------- #
@pytest.fixture(scope="session")
def cli_login(api_host, users_api_service, user, user_email, user_password):
    runner = CliRunner()
    cli_response = runner.invoke(
        cli,
        [
            "app",
            "login",
            "--email",
            user_email,
            "--password",
            user_password,
            "--alias",
            "test",
        ],
    )
    assert cli_response.exit_code == 0, cli_response.output
    yield
    runner.invoke(cli, ["app", "logout", "--alias", "test"])


@pytest.fixture
def cli_temporary_logout():
    folder = os.path.expanduser("~/.pogam/")
    credentials_path = os.path.join(folder, "credentials")
    try:
        with open(credentials_path, "r") as f:
            all_credentials = json.load(f)
    except FileNotFoundError:
        all_credentials = {}

    def _logout(alias="test"):
        all_credentials_temp = {
            k: all_credentials[k] for k in all_credentials if k != alias
        }
        with open(credentials_path, "w") as f:
            json.dump(all_credentials_temp, f)

    yield _logout
    with open(credentials_path, "w") as f:
        json.dump(all_credentials, f)


# ------------------------------------- Local DB ------------------------------------- #
@pytest.fixture()
def in_memory_db():
    tmp = os.getenv("POGAM_DATABASE_URL")
    os.environ["POGAM_DATABASE_URL"] = "sqlite://"
    yield
    if tmp is not None:
        os.environ["POGAM_DATABASE_URL"] = tmp
