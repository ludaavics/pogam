import contextlib
import itertools as it
import os
import re
import warnings

import pytest
from httmock import HTTMock, all_requests

from pogam.scrapers import proxies

# modified version of https://www.regular-expressions.info/ip.html
is_ip_address = re.compile(
    r"^(http(s)?://)?"
    r"(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}"
    r"(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)"
    r"(:\d+)?$"
)


@pytest.fixture
def unavailable_proxy():
    @all_requests
    def response(url, request):
        return {"status_code": 500, "content": ""}

    return response


@pytest.mark.parametrize("infinite", [True, False])
@pytest.mark.parametrize("errors", ["raise", "warn"])
@pytest.mark.parametrize("proxy_is_down", [True, False])
@pytest.mark.parametrize(
    "proxy_name, proxy_kwargs",
    [
        ("proxylist", {}),
        ("proxylist", {"protocol": "http"}),
        ("proxylist", {"protocol": "https"}),
        ("proxy11", {}),
        ("all_proxies", {}),
    ],
)
def test_get_proxy_pool(
    infinite, errors, proxy_name, proxy_kwargs, proxy_is_down, unavailable_proxy
):
    """
    Create a proxy pool from a given source.
    """
    proxy_kwargs.update({"infinite": infinite, "errors": errors})
    if proxy_name == "proxy11":
        proxy_kwargs.update({"api_key": os.getenv("PROXY11_API_KEY")})

    if proxy_is_down:
        request_context_manager = HTTMock(unavailable_proxy)

        if errors == "warn":
            match = re.compile(r"^Failed to get.*Proceeding.*", re.DOTALL)
            pytest_context_manager = pytest.warns(UserWarning, match=match)
        else:
            assert errors == "raise"
            match = r"(?:^Failed\S*)((?!Proceeding).)*$"
            pytest_context_manager = pytest.raises(RuntimeError, match=match)
    else:
        request_context_manager = contextlib.nullcontext()
        pytest_context_manager = contextlib.nullcontext()

    warning_filter = (
        "ignore" if (proxy_name == "all_proxies" and errors == "raise") else "default"
    )
    with request_context_manager:
        with warnings.catch_warnings():
            warnings.simplefilter(warning_filter)
            with pytest_context_manager:
                proxy_pool = getattr(proxies, proxy_name)(**proxy_kwargs)

    if proxy_is_down:
        return

    # make sure we honor the infinite parameter
    expected = it.cycle if infinite else list
    assert isinstance(proxy_pool, expected)

    # make sure we actually get IP addresses
    n = 10 if infinite else len(proxy_pool)
    assert all([re.match(is_ip_address, proxy) for proxy in it.islice(proxy_pool, n)])
