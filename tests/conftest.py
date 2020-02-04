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


# ----------------------------- AWS Services Fixtures -------------------------------- #
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
