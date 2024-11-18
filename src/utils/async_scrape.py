"""
Work in progress async concurrent scraper
"""

from dataclasses import dataclass
from datetime import timedelta
from typing import List, Optional
import asyncio
import aiohttp
import diskcache
from loguru import logger

from .scrape import _USER_AGENT


@dataclass
class Response:
    """Minimal response wrapper to work around aiohttp's response object which defers the reading of the response body"""

    url: str
    status: int
    content_type: Optional[str] = None
    text: Optional[str] = None

    @property
    def ok(self) -> bool:
        return 200 <= self.status < 300


# Example headers
headers = {
    "User-Agent": _USER_AGENT,
    "Accept": "text/html",
}

def key(url: str) -> str:
    return f"async_scrape:{url}"

async def request_url(session: aiohttp.ClientSession, url: str, cache: Optional[diskcache.Cache] = None) -> Response:
    # TODO: I dislike this caching design; I'd rather have it be  something that can be composed with the top-level scrape function
    if cache:
        response = cache.get(key(url))
        if response:
            return response

    try:
        async with session.get(url, verify_ssl=False) as raw_response:
            response = Response(
                url=url,
                status=raw_response.status,
            )

            if response.ok:
                response.content_type = raw_response.headers.get("Content-Type")

                # TODO: Consider allowing configuration of content types
                if response.content_type.startswith("text/html"):
                    try:
                        response.text = await raw_response.text()
                    except UnicodeDecodeError:
                        logger.error(f"UnicodeDecodeError on {url}")
            if cache:
                cache.set(key(url), response, expire=timedelta(days=20).total_seconds())
    except TimeoutError:
        response = Response(url=url, status=504)

    return response


async def scrape(
    urls: List[str], connection_limit=10, connection_limit_per_host=1, timeout_seconds=2, cache: Optional[diskcache.Cache] = None
) -> List[Response]:
    """
    Concurrently scrape a list of URLs. In early testing, the overall speed is limited by the timeout.

    Args:
        urls: List of URLs to scrape
        connection_limit: Maximum number of concurrent connections
        connection_limit_per_host: Maximum number of concurrent connections per host
        timeout_seconds: Timeout for each request
        cache: Optional diskcache.Cache for caching responses
    """
    connector = aiohttp.TCPConnector(
        limit=connection_limit, limit_per_host=connection_limit_per_host
    )
    async with aiohttp.ClientSession(
        connector=connector,
        headers=headers,
        timeout=aiohttp.ClientTimeout(total=timeout_seconds),
    ) as session:
        futures = [request_url(session, url, cache=cache) for url in urls]

        responses = await asyncio.gather(*futures)

    return responses
