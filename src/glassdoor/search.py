# search for a company
from googlesearch import search
from core import CompanyProduct
import re


def find_review_url(target: CompanyProduct, pause_seconds=2, debug=False):
    """Find the URL Glassdoor review page for a company"""
    query = f'site:www.glassdoor.com/Reviews/ "{target.company}""'

    urls = list(
        url
        for url in search(query, num=10, stop=10, pause=pause_seconds)
        if re.match(r".*-Reviews-.*", url)
    )

    if debug:
        print(urls)

    return urls[0]
