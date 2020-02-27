import os

import pytest
from httmock import HTTMock, response, urlmatch
from requests.compat import urlparse

from pogam.scrapers.seloger import _to_seloger_geographical_code, _seloger
from pogam.scrapers import exceptions

here = os.path.dirname(__file__)
root_folder = os.path.abspath(os.path.join(here, ".."))
fixtures_folder = os.path.join(root_folder, "tests", "fixtures", "seloger")


# ------------------------------------------------------------------------------------ #
#                                        Fixture                                       #
# ------------------------------------------------------------------------------------ #
@pytest.fixture
def seloger_fields_not_found():
    url = "https://seloger-fields-not-found.test"
    netloc = urlparse(url).netloc
    with open(os.path.join(fixtures_folder, "fields-not-found.html")) as f:
        html = f.read()

    @urlmatch(netloc=netloc)
    def mock_response(url, request):
        return response(200, html, request=request)

    return {"url": url, "mock_response": mock_response}


# ------------------------------------------------------------------------------------ #
#                                         Tests                                        #
# ------------------------------------------------------------------------------------ #
def test_seloger_fields_not_found(seloger_fields_not_found):
    """
    Listing without the fields to parse should raise a ListingParsingError
    """
    url = seloger_fields_not_found["url"]
    mock_response = seloger_fields_not_found["mock_response"]
    with HTTMock(mock_response):
        match = r".*not find.*HTML source.*"
        with pytest.raises(exceptions.ListingParsingError, match=match):
            _seloger(url)


@pytest.mark.parametrize(
    "post_code,seloger_code",
    [
        ("92200", ("ci", "920051")),
        (92200, ("ci", "920051")),
        ("75016", ("ci", "750116")),
        ("75116", ("ci", "750116")),
        ("93", ("cp", "93")),
        ("75", ("cp", "75")),
        ("69", ("cp", "69")),
    ],
)
def test_to_known_seloger_code(post_code, seloger_code):
    """
    Known valid post code should yield known (modified) insee codes.
    """
    expected = seloger_code
    actual = _to_seloger_geographical_code(post_code)
    assert expected == actual


@pytest.mark.parametrize("post_code", [-1, "hello", None, 9999])
def test_invalid_post_code(post_code):
    """
    Invalid post codes should raise ValueError.
    """
    expected_error_message = f"Unknown post code '{post_code}'."
    with pytest.raises(ValueError, match=expected_error_message):
        _to_seloger_geographical_code(post_code)
