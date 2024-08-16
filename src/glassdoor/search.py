# search for a company
from core import CompanyProduct
import re
from functools import lru_cache
from search import search, SearchResult

@lru_cache(1000)
def find_review(target: CompanyProduct, debug=False) -> SearchResult:
    """Find the Glassdoor review page for a company"""
    query = f'site:www.glassdoor.com/Reviews/ "{target.company}"'

    urls = list(search(query, num=10))
    if debug:
        print("find_review:Search results", urls)

    # Filter
    urls = [url for url in urls if re.match(r".*/Reviews/(.*)-Reviews-E([0-9A-F]+).htm.*", url.link)]

    if debug:
        print("find_review: Filtered results", urls)

    return urls[0]



def find_review_url(target: CompanyProduct, debug=False) -> str:
    """Find the URL Glassdoor review page for a company"""

    return find_review(target, debug=debug).link