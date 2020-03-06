import json
import os

import pytest
from httmock import HTTMock, response, urlmatch
import requests

from pogam import create_app
from pogam.scrapers.leboncoin import leboncoin

app = create_app("cli")

here = os.path.dirname(__file__)
root_folder = os.path.abspath(os.path.join(here, ".."))
fixtures_folder = os.path.join(root_folder, "tests", "fixtures", "leboncoin")


# ------------------------------------------------------------------------------------ #
#                                       Fixtures                                       #
# ------------------------------------------------------------------------------------ #
@pytest.fixture
def make_search_and_response():
    def _make_search_and_response(name):
        with open(os.path.join(fixtures_folder, name + ".json"), "r") as f:
            search_and_response = json.load(f)
        search = search_and_response["search"]
        _response = search_and_response["response"]

        @urlmatch(
            netloc="api.leboncoin.fr", path="/api/adfinder/v1/search", method="post"
        )
        def mock_response(url, request):
            return response(200, _response, request=request)

        return {"search": search, "response": mock_response}

    return _make_search_and_response


@pytest.fixture
def make_error_response():
    def _make_error_response(exception):
        @urlmatch(
            netloc="api.leboncoin.fr", path="/api/adfinder/v1/search", method="post"
        )
        def mock_response(url, request):
            raise exception

        return mock_response

    return _make_error_response


@pytest.fixture
def mock_captcha():
    @urlmatch(netloc="api.leboncoin.fr", path="/api/adfinder/v1/search", method="post")
    def mock_response(url, request):
        return response(200, "captcha")

    return mock_response


# ------------------------------------------------------------------------------------ #
#                                         Tests                                        #
# ------------------------------------------------------------------------------------ #
@pytest.mark.parametrize("name", ["success"])
def test_known_query(name, make_search_and_response, mock_proxies, in_memory_db):
    search_and_response = make_search_and_response(name)
    search = search_and_response["search"]
    mock_response = search_and_response["response"]
    with HTTMock(mock_response):
        with app.app_context():
            leboncoin(**search)


@pytest.mark.parametrize("exception_name", ["proxy", "timeout"])
def test_request_error(exception_name, make_error_response, mock_proxies, in_memory_db):
    exception = {
        "proxy": requests.exceptions.ProxyError,
        "timeout": requests.exceptions.Timeout,
    }[exception_name]
    mock_response = make_error_response(exception)
    with HTTMock(mock_response):
        with app.app_context():
            match = r"Failed to reach .*"
            with pytest.raises(RuntimeError, match=match):
                leboncoin("rent", "92130")


def test_captcha(mock_captcha, mock_proxies, in_memory_db):
    with HTTMock(mock_captcha):
        with app.app_context():
            match = r"Failed to reach .*"
            with pytest.raises(RuntimeError, match=match):
                leboncoin("rent", "92130")
