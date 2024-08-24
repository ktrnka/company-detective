import re
from functools import lru_cache
from typing import Optional
from loguru import logger

from core import CompanyProduct
from google_search import search, SearchResult


@lru_cache(1000)
def find_review(target: CompanyProduct) -> Optional[SearchResult]:
    """Find the Glassdoor review page for a company"""
    query = f'site:www.glassdoor.com/Reviews/ "{target.company}"'

    urls = list(search(query, num=10))
    logger.debug("Search results {}", urls)

    # Filter
    urls = [url for url in urls if re.match(r".*/Reviews/(.*)-Reviews-E([0-9A-F]+).htm.*", url.link)]

    logger.debug("Filtered results {}", urls)

    if not urls:
        return None

    return urls[0]



def find_review_url(target: CompanyProduct, debug=False) -> str:
    """Find the URL Glassdoor review page for a company"""

    return find_review(target, debug=debug).link