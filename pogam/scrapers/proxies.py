import requests
import itertools as it
from typing import Optional
import logging

logger = logging.getLogger(__name__)


def proxy11(
    api_key: str,
    *,
    port: Optional[int] = None,
    type_: Optional[str] = None,
    country: Optional[str] = None,
    limit: Optional[int] = None,
    speed: Optional[int] = None,
    errors: str = "raise",
):
    """
    Infinite iterator of proxies from proxy11.com.

    api_key: require API key.
    port: limit proxies to a specific port.
    type_: limit results to only 'anonymous' or 'transparent'.
    country: limit results to a specific location.
    limit: maximum number of results.
    speed: limit proxies below a given timeout.
    errors: 'warn' or 'raise'. When proxy retrieval fails, either warn but go on,
        or raise a RuntimeError.
    """
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
            proxy_iter = it.cycle([None])
        else:
            raise RuntimeError(msg)
    else:
        proxy_iter = it.cycle(response.text.split())
    return proxy_iter
