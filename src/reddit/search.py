import re
from googlesearch import search


from functools import lru_cache
from typing import Iterable

from core import CompanyProduct


REDDIT_COMMENTS_URL_PATTERN = re.compile(r".*/comments/.+")


@lru_cache(1000)
def find_submission_urls(
    target: CompanyProduct, results_per_page=10, num_results=10, pause_seconds=2
) -> Iterable[str]:
    query = f'site:reddit.com "{target.company}""'
    if target.product != target.company:
        query += f' "{target.product}"'

    return list(
        url
        for url in search(
            query, num=results_per_page, stop=num_results, pause=pause_seconds
        )
        if REDDIT_COMMENTS_URL_PATTERN.match(url)
    )


def test_search():
    """Test that we can issue a Google search against Reddit and get some results"""
    for url in find_submission_urls(
        CompanyProduct("Singularity 6", "Palia"), num_results=20
    ):
        print(url)
