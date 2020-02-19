import itertools as it
import os
import re

import pytest

from pogam.scrapers import proxies

# modified version of https://www.regular-expressions.info/ip.html
is_ip_address = re.compile(
    r"^(http(s)?://)?"
    r"(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}"
    r"(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)"
    r"(:\d+)?$"
)


@pytest.mark.parametrize(
    "proxy_name, proxy_kwargs",
    [
        ("proxylist", {}),
        ("proxylist", {"infinite": False}),
        ("proxylist", {"protocol": "http"}),
        ("proxylist", {"protocol": "https"}),
        ("proxy11", {}),
        ("proxy11", {"infinite": False}),
        ("all_proxies", {}),
        ("all_proxies", {"infinite": False}),
    ],
)
def test_get_proxy_pool(proxy_name, proxy_kwargs):
    """
    Create a proxy pool from a given source.
    """
    if proxy_name == "proxy11":
        proxy_kwargs.update({"api_key": os.getenv("PROXY11_API_KEY")})
    proxy_pool = getattr(proxies, proxy_name)(**proxy_kwargs)

    # make sure we honor the infinite parameter
    infinite = proxy_kwargs.get("infinite", True)
    expected = it.cycle if infinite else list
    assert isinstance(proxy_pool, expected)

    # make sure we actually get IP addresses
    n = 10 if infinite else len(proxy_pool)
    assert all([re.match(is_ip_address, proxy) for proxy in it.islice(proxy_pool, n)])

    # TODO: fixture / test case for when proxy server goes down (getting None's)
