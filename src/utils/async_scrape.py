"""
Work in progress async concurrent scraper
"""

from typing import List, Dict, Mapping
from collections import defaultdict
from urllib.parse import urlparse
from itertools import chain
import asyncio
from typing import List, Dict, Tuple
import aiohttp

from .scrape import _USER_AGENT

def group_urls_by_domain(urls: List[str]) -> Mapping[str, List[str]]:
    grouped_urls = defaultdict(list)
    for url in urls:
        domain = urlparse(url).netloc
        grouped_urls[domain].append(url)
    return grouped_urls


async def request_urls(session: aiohttp.ClientSession, urls: List[str]) -> List[Tuple]:
    responses = []
    for i, url in enumerate(sorted(urls)):
        try:
            async with session.get(url, allow_redirects=False) as response:
                if response.ok:
                    try:
                        # TODO: Replace this with a basic model
                        responses.append((url, response.status, await response.text()))
                    except UnicodeDecodeError:
                        responses.append((url, response.status, None))
                else:
                    responses.append((url, response.status, None))
        except TimeoutError:
            responses.append((url, 504, None))

    return responses


# Example headers
headers = {
    "User-Agent": _USER_AGENT,
    "Accept": "text/html",
}


async def scrape(urls: List[str]) -> List[str]:
    # TODO: This is no longer needed due to limit_per_host
    grouped_urls = group_urls_by_domain(urls)

    # TODO: Expose the concurrency settings
    connector = aiohttp.TCPConnector(limit=10, limit_per_host=1)
    async with aiohttp.ClientSession(
        # TODO: Expose the timeout setting
        connector=connector, headers=headers, timeout=aiohttp.ClientTimeout(total=2)
    ) as session:
        futures = [request_urls(session, urls) for urls in grouped_urls.values()]

        domain_responses = await asyncio.gather(*futures)

    return list(chain(*domain_responses))
