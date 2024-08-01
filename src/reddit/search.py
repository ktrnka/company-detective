import re


from functools import lru_cache
from typing import Iterable

from core import CompanyProduct
from search import search, SearchResult


REDDIT_COMMENTS_URL_PATTERN = re.compile(r".*/comments/.+")


def find_submission_urls(target: CompanyProduct, num_results=10) -> Iterable[str]:
    return [result.link for result in find_submissions(target, num_results=num_results)]

@lru_cache(1000)
def find_submissions(target: CompanyProduct, num_results=10):
    # NOTE: Ideally we probably want more than 10 results and need to paginate
    query = f'site:reddit.com "{target.company}""'
    if target.product != target.company:
        query += f' "{target.product}"'

    return list(
        result
        for result in search(query, num=num_results)
        if REDDIT_COMMENTS_URL_PATTERN.match(result.link)
    )

def test_search():
    """Test that we can issue a Google search against Reddit and get some results"""
    for url in find_submission_urls(
        CompanyProduct("Singularity 6", "Palia"), num_results=10
    ):
        print(url)
