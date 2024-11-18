"""
Work in progress async concurrent scraper
"""

from dataclasses import dataclass
from typing import List, Mapping, Optional
from collections import defaultdict
from urllib.parse import urlparse
import asyncio
import aiohttp
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

def group_urls_by_domain(urls: List[str]) -> Mapping[str, List[str]]:
    grouped_urls = defaultdict(list)
    for url in urls:
        domain = urlparse(url).netloc
        grouped_urls[domain].append(url)
    return grouped_urls


# Example headers
headers = {
    "User-Agent": _USER_AGENT,
    "Accept": "text/html",
}

async def request_url(session: aiohttp.ClientSession, url: str) -> Response:
    try:
        async with session.get(url) as response:
            response = Response(
                url=url,
                status=response.status,
            )

            if response.ok:
                response.content_type = response.headers.get("Content-Type")

                if response.content_type == "text/html":
                    try:
                        response.text = await response.text()
                    except UnicodeDecodeError:
                        logger.error(f"UnicodeDecodeError on {url}")
    except TimeoutError:
        response = Response(url=url, status=504)

    return response

async def scrape(urls: List[str], connection_limit=10, connection_limit_per_host=1, timeout_seconds=2) -> List[Response]:
    # These connector settings effectively control concurrency
    connector = aiohttp.TCPConnector(limit=connection_limit, limit_per_host=connection_limit_per_host)
    async with aiohttp.ClientSession(
        connector=connector, headers=headers, timeout=aiohttp.ClientTimeout(total=timeout_seconds)
    ) as session:
        futures = [request_url(session, url) for url in urls]

        responses = await asyncio.gather(*futures)

    return responses
