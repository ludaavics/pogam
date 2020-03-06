import json
import os

import pytest
from httmock import HTTMock, response, urlmatch

from pogam import create_app
from pogam.scrapers.leboncoin import leboncoin

app = create_app("cli")

here = os.path.dirname(__file__)
root_folder = os.path.abspath(os.path.join(here, ".."))
fixtures_folder = os.path.join(root_folder, "tests", "fixtures", "leboncoin")


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
            # check that the payload is indeed the search
            return response(200, _response, request=request)

        return {"search": search, "response": mock_response}

    return _make_search_and_response


@pytest.mark.parametrize("name", ["success"])
def test_known_query(name, make_search_and_response, mock_proxies, in_memory_db):
    search_and_response = make_search_and_response(name)
    search = search_and_response["search"]
    mock_response = search_and_response["response"]
    with HTTMock(mock_response):
        with app.app_context():
            leboncoin(**search)
