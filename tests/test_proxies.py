import contextlib
import itertools as it
import os
import re
import warnings

import pytest
from httmock import HTTMock, all_requests, response, urlmatch

from pogam.scrapers import proxies

# modified version of https://www.regular-expressions.info/ip.html
is_ip_address = re.compile(
    r"^(http(s)?://)?"
    r"(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}"
    r"(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)"
    r"(:\d+)?$"
)


# ------------------------------------------------------------------------------------ #
#                                       Fixtures                                       #
# ------------------------------------------------------------------------------------ #
@pytest.fixture
def unavailable_proxy():
    @all_requests
    def mock_response(url, request):
        return {"status_code": 500, "content": ""}

    return mock_response


@pytest.fixture
def mock_proxylist():
    content = """
    138.68.41.90:3128
    138.68.41.90:8080
    138.68.240.218:3128
    138.68.24.145:3128
    138.197.222.35:8080
    138.197.222.35:3128
    138.68.24.145:8080
    159.203.91.6:3128
    159.203.91.6:8080
    159.203.166.41:8080
    159.203.166.41:3128
    167.172.57.5:8118
    165.227.215.62:3128
    """

    def _make_response(proxy_is_down):
        @urlmatch(netloc="www.proxy-list.download")
        def mock_response(url, request):
            if proxy_is_down:
                return {"status_code": 500, "content": ""}
            return response(
                200, content=content, headers={"Content-Type": "text/plain"}
            )

        return mock_response

    return {"name": "proxylist", "response": _make_response}


@pytest.fixture
def mock_proxy11():
    content = """
    1.0.0.103:80
    1.0.0.5:80
    1.0.0.92:80
    87.255.27.169:3128
    51.158.108.135:8811
    104.17.116.167:80
    1.0.0.45:80
    178.62.204.137:80
    1.0.0.253:80
    188.166.83.17:3128
    84.17.47.182:80
    213.175.42.220:3128
    1.0.0.34:80
    1.0.0.141:80
    95.31.119.210:31135
    176.114.128.131:3128
    """

    def _make_response(proxy_is_down):
        @urlmatch(netloc="proxy11.com")
        def mock_response(url, request):
            if proxy_is_down:
                return {"status_code": 500, "content": ""}
            return response(
                200, content=content, headers={"Content-Type": "text/plain"}
            )

        return mock_response

    return {"name": "proxy11", "response": _make_response}


@pytest.fixture
def mock_proxies(mock_proxylist, mock_proxy11):
    return [mock_proxylist, mock_proxy11]


@pytest.fixture(
    params=[
        ("proxylist", {}),
        ("proxylist", {"protocol": "http"}),
        ("proxylist", {"protocol": "https"}),
        ("proxy11", {}),
        ("all_proxies", {}),
    ]
)
def proxy_calls(request):
    return request.param


@pytest.fixture
def no_proxy11_api_key():
    try:
        proxy11_api_key = os.environ.pop("PROXY11_API_KEY")
    except KeyError:
        proxy11_api_key = None
    yield
    if proxy11_api_key:
        os.environ["PROXY11_API_KEY"] = proxy11_api_key


# ------------------------------------------------------------------------------------ #
#                                         Tests                                        #
# ------------------------------------------------------------------------------------ #
@pytest.mark.parametrize("infinite", [True, False])
@pytest.mark.parametrize("errors", ["raise", "warn"])
@pytest.mark.parametrize(
    "proxies_are_down", [["proxylist"], ["proxy11"], ["proxylist", "proxy11"]]
)
def test_get_proxy_pool(
    infinite, errors, proxy_calls, proxies_are_down, unavailable_proxy, mock_proxies
):
    """
    Create a proxy pool from a given source.
    """
    proxy_name, proxy_kwargs = proxy_calls
    proxy_kwargs.update({"infinite": infinite, "errors": errors})
    if proxy_name == "proxy11":
        proxy_kwargs.update({"api_key": os.getenv("PROXY11_API_KEY")})

    # mock the proxies
    request_context_managers = []
    are_proxies_down = []
    for mock_proxy in mock_proxies:
        mock_proxy_name = mock_proxy["name"]
        mock_proxy_response = mock_proxy["response"]
        proxy_is_down = mock_proxy_name in proxies_are_down
        request_context_managers.append(HTTMock(mock_proxy_response(proxy_is_down)))
        are_proxies_down.append(proxy_is_down)

    # if the proxy we're testing is down, set up the appropriate pytest context manager
    all_proxies_are_down = (proxy_name in proxies_are_down) or (
        proxy_name == "all_proxies" and (all(are_proxies_down))
    )
    if all_proxies_are_down:
        if errors == "warn":
            match = re.compile(r"^Failed to get.*Proceeding.*", re.DOTALL)
            pytest_context_manager = pytest.warns(UserWarning, match=match)
        else:
            assert errors == "raise"
            match = r"(?:^Failed\S*)((?!Proceeding).)*$"
            pytest_context_manager = pytest.raises(RuntimeError, match=match)
    else:
        pytest_context_manager = contextlib.nullcontext()

    warning_filter = (
        "ignore" if (proxy_name == "all_proxies" and errors == "raise") else "default"
    )

    with contextlib.ExitStack() as stack:
        for request_context_manager in request_context_managers:
            stack.enter_context(request_context_manager)
        with warnings.catch_warnings():
            warnings.simplefilter(warning_filter)
            with pytest_context_manager:
                proxy_pool = getattr(proxies, proxy_name)(**proxy_kwargs)

    if all_proxies_are_down:
        return

    # make sure we honor the infinite parameter
    expected = it.cycle if infinite else list
    assert isinstance(proxy_pool, expected)

    # make sure we actually get IP addresses
    n = 10 if infinite else len(proxy_pool)
    assert all([re.match(is_ip_address, proxy) for proxy in it.islice(proxy_pool, n)])


def test_invalid_errors_param(proxy_calls):
    proxy_name, proxy_kwargs = proxy_calls
    proxy_kwargs.update({"errors": "foo"})
    if proxy_name == "proxy11":
        proxy_kwargs.update({"api_key": os.getenv("PROXY11_API_KEY")})

    match = "'errors' must be 'warn' or 'raise'. Got 'foo' instead."
    with pytest.raises(ValueError, match=match):
        getattr(proxies, proxy_name)(**proxy_kwargs)


@pytest.mark.parametrize(
    "api_key, exception, message",
    [
        ("", ValueError, r".*key is missing.*"),
        (None, ValueError, r".*key is missing.*"),
        ("foo", RuntimeError, r".*Failed to get proxies*"),
    ],
)
def test_proxy11_wrong_api_key(api_key, exception, message):
    with pytest.raises(exception, match=message):
        proxies.proxy11(api_key=api_key)


def test_all_proxies_missing_proxy11_api_key(no_proxy11_api_key, mock_proxies):
    assert os.getenv("PROXY11_API_KEY") is None
    with contextlib.ExitStack() as stack:
        for mock_proxy in mock_proxies:
            stack.enter_context(HTTMock(mock_proxy["response"](proxy_is_down=False)))
        proxy_pool = proxies.all_proxies(infinite=False)
    assert all([re.match(is_ip_address, proxy) for proxy in proxy_pool])
