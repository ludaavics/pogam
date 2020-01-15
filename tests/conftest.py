import os
import subprocess
import uuid
import logging
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
        help="Run tests that require the deployment of the app's services.",
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
def stage():
    return f"test-{str(uuid.uuid4()).split('-')[0]}"


@pytest.fixture
def shared_resources_service(stage):
    logger.info(f"Deploying shared-resources service to stage {stage}...")
    folder = os.path.join(root_folder, "app", "shared-resources")
    subprocess.run(["sls", "deploy", "--stage", stage], cwd=folder)
    yield
    logger.info(f"Taking down shared-resources service from stage {stage}...")
    subprocess.run(["sls", "remove", "--stage", stage], cwd=folder)


@pytest.fixture
def scrapes_api_service(shared_resources_service, stage):
    logger.info(f"Deploying scrapes-api service to stage {stage}...")
    folder = os.path.join(root_folder, "app", "scrapes-api")
    subprocess.run(["sls", "deploy", "--stage", stage], cwd=folder)
    yield
    logger.info(f"Taking down scrapes-api service from stage {stage}...")
    subprocess.run(["sls", "remove", "--stage", stage], cwd=folder)


@pytest.fixture
def scrape_schedules_api_service(scrapes_api_service, stage):
    logger.info(f"Deploying scrape-schedule-api service to stage {stage}...")
    folder = os.path.join(root_folder, "app", "scrape-schedules-api")
    subprocess.run(["sls", "deploy", "--stage", stage], cwd=folder)
    yield
    logger.info(f"Taking down scrape-schedule-api service from stage {stage}...")
    subprocess.run(["sls", "remove", "--stage", stage], cwd=folder)
