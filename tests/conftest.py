import os

import pytest


@pytest.fixture
def api_host():
    original_host = os.getenv("POGAM_API_HOST")
    test_host = os.getenv("POGAM_TEST_API_HOST")
    if test_host is None:
        msg = "Missing 'POGAM_API_HOST' environment variable."
        raise ValueError(msg)
    os.environ["POGAM_API_HOST"] = test_host
    yield
    os.environ["POGAM_API_HOST"] = original_host
