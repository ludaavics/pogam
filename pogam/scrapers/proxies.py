import itertools as it
import logging
import os
from typing import Optional
import random

import requests

logger = logging.getLogger(__name__)


def all_proxies(*, infinite=True):
    """
    Aggregate results from multiplie proxies into a single pool.
    """
    results = []

    # proxy11.com
    api_key = os.getenv("PROXY11_API_KEY")
    if api_key:
        results += proxy11(
            api_key, type_="anonymous", speed=2, infinite=False, errors="warn"
        )

    # proxy-list.download
    results += proxylist(infinite=False, errors="warn")

    # aggregate
    if set(results) == {None}:
        msg = f"Failed to get any proxy. Proceeding without."
        logger.warn(msg)
    else:
        results = [result for result in results if result is not None]
    random.shuffle(results)
    proxy_iter = it.cycle(results) if infinite else results
    return proxy_iter


def proxylist(*, protocol="https", infinite=True, errors="raise"):
    """
    Return an iterator of proxies from proxy-list.download.

    Args:
        infinite: True to return an infinite iterator.
        errors: 'warn' or 'raise'. When proxy retrieval fails, either warn but go on,
            or raise a RuntimeError.
    """
    response = requests.get(
        "https://www.proxy-list.download/api/v1/get", params={"type": protocol}
    )
    if response.status_code >= 400:
        msg = (
            f"Failed to get proxies from proxy-list.download. "
            f"Got status code {response.status_code} "
            f"and response {response.text}"
        )
        if errors == "warn":
            msg += "\nProceeding without proxy."
            logger.warn(msg)
            proxy_list = [None]
        else:
            raise RuntimeError(msg)
    else:
        proxy_list = ["http://" + proxy for proxy in response.text.split()]
        random.shuffle(proxy_list)

    proxy_iter = it.cycle(proxy_list) if infinite else proxy_list
    return proxy_iter


def proxy11(
    api_key: str,
    *,
    port: Optional[int] = None,
    type_: Optional[str] = None,
    country: Optional[str] = None,
    limit: Optional[int] = None,
    speed: Optional[int] = None,
    infinite: bool = True,
    errors: str = "raise",
):
    """
    Return an iterator of proxies from proxy11.com.

    api_key: require API key.
    port: limit proxies to a specific port.
    type_: limit results to only 'anonymous' or 'transparent'.
    country: limit results to a specific location.
    limit: maximum number of results.
    speed: limit proxies below a given timeout.
    infinite: True to return an infinite iterator.
    errors: 'warn' or 'raise'. When proxy retrieval fails, either warn but go on,
        or raise a RuntimeError.
    """
    if errors not in ["warn", "raise"]:
        msg = f"'errors' must be 'warn' or 'raise'. Got '{errors}' instead."
        raise ValueError(msg)

    url = "https://proxy11.com/api/proxy.txt"
    if not api_key:
        msg = "Proxy 11 API key is missing."
        raise ValueError(msg)
    data = {
        "key": api_key,
        "port": port,
        "type": type_,
        "country": country,
        "limit": limit,
        "speed": speed,
    }
    data = {k: data[k] for k in data if data[k] is not None}
    response = requests.get(url, data)
    if (response.status_code >= 400) or ("error" in response.text):
        msg = (
            f"Failed to get proxies from proxy11.com. "
            f"Got status code {response.status_code} "
            f"and response {response.text}"
        )
        if errors == "warn":
            msg += "\nProceeding without proxy."
            logger.warn(msg)
            proxy_list = [None]
        else:
            raise RuntimeError(msg)
    else:
        proxy_list = ["http://" + proxy for proxy in response.text.split()]
        random.shuffle(proxy_list)

    proxy_iter = it.cycle(proxy_list) if infinite else proxy_list
    return proxy_iter
