# search for a company
from core import CompanyProduct
import re
from functools import lru_cache
from search import search


@lru_cache(1000)
def find_review_url(target: CompanyProduct, debug=False):
    """Find the URL Glassdoor review page for a company"""
    query = f'site:www.glassdoor.com/Reviews/ "{target.company}""'

    urls = list(
        url for url in search(query, num=10) if re.match(r".*-Reviews-.*", url.link)
    )

    if debug:
        print(urls)

    return urls[0].link
