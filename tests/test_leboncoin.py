import json
import logging
import math
import os
from copy import deepcopy

import pytest
import requests
from httmock import HTTMock, response, urlmatch

from pogam import create_app
from pogam.scrapers.leboncoin import leboncoin

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
        original_ads = deepcopy(_response["ads"])

        page = 0
        page_length = 50
        last_page = math.ceil(len(original_ads) / page_length)

        @urlmatch(
            netloc="api.leboncoin.fr", path="/api/adfinder/v1/search", method="post"
        )
        def mock_response(url, request):
            nonlocal page
            _response["ads"] = original_ads[
                page * page_length : (page + 1) * page_length
            ]
            if page == last_page:
                _response.pop("pivot")
            page += 1
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


@pytest.fixture
def mock_image():
    i = 0

    @urlmatch(netloc=r".*img.*.leboncoin.fr.*")
    def mock_response(url, request):
        nonlocal i
        if i % 10 == 0:
            return response(500)
        with open(os.path.join(fixtures_folder, "img.jpg"), "rb") as f:
            return response(200, f.read())

    return mock_response


# ------------------------------------------------------------------------------------ #
#                                         Tests                                        #
# ------------------------------------------------------------------------------------ #
@pytest.mark.parametrize(
    "name, overrides",
    [
        ("success", {}),
        (
            "success",
            {
                "num_results": 5,
                "min_rooms": 1,
                "max_rooms": 3,
                "min_size": 30,
                "max_size": 50,
                "min_price": 500,
                "max_price": 1500,
            },
        ),
    ],
)
def test_known_query(
    name,
    overrides,
    make_search_and_response,
    mock_image,
    mock_proxies,
    in_memory_db,
    images_folder,
    caplog,
):
    search_and_response = make_search_and_response(name)
    search = search_and_response["search"]
    search.update(overrides)
    mock_response = search_and_response["response"]
    app = create_app("cli")
    with HTTMock(mock_response), HTTMock(mock_image), app.app_context():
        # some of the fixtures' listing are deliebarately malformed
        # the code is robust to them but they are logged for debugging purposes
        # we don't want to print them out, during the test suite.
        with caplog.at_level(logging.CRITICAL):
            leboncoin(**search)


@pytest.mark.parametrize("exception_name", ["proxy", "timeout"])
def test_request_error(exception_name, make_error_response, mock_proxies, in_memory_db):
    exception = {
        "proxy": requests.exceptions.ProxyError,
        "timeout": requests.exceptions.Timeout,
    }[exception_name]
    mock_response = make_error_response(exception)
    app = create_app("cli")
    with HTTMock(mock_response):
        with app.app_context():
            match = r"Failed to reach .*"
            with pytest.raises(RuntimeError, match=match):
                leboncoin("rent", "92130")


def test_captcha(mock_captcha, mock_proxies, in_memory_db):
    app = create_app("cli")
    with HTTMock(mock_captcha):
        with app.app_context():
            match = r"Failed to reach .*"
            with pytest.raises(RuntimeError, match=match):
                leboncoin("rent", "92130")


@pytest.mark.parametrize(
    "inputs, exception, match",
    [
        ({"transaction": "foo"}, ValueError, r"Unknown transaction.*foo.*"),
        ({"property_types": "foo"}, ValueError, r"Unknown property_type.*foo.*"),
    ],
)
def test_invalid_inputs(
    inputs, exception, match, make_search_and_response, mock_proxies, in_memory_db
):
    search_and_response = make_search_and_response("success")
    mock_response = search_and_response["response"]
    search = {"transaction": "rent", "post_codes": ["92130"]}
    search.update(inputs)
    app = create_app("cli")
    with HTTMock(mock_response):
        with app.app_context():
            with pytest.raises(exception, match=match):
                leboncoin(**search)
