import re


from functools import lru_cache
from typing import Iterable, List, Optional

from core import Seed
from src.utils.google_search import search


REDDIT_COMMENTS_URL_PATTERN = re.compile(r".*/comments/.+")


def find_submission_urls(target: Seed, num_results=10) -> Iterable[str]:
    return [result.link for result in find_submissions(target, num_results=num_results)]

def build_keywords(keywords: Optional[Iterable[str]]) -> str:
    if not keywords:
        return ""
    
    if len(keywords) > 1:
        return "({})".format(" OR ".join(keywords))
    else:
        # Note: Somewhat annoying because I had to store it as a frozenset to be cacheable
        return next(iter(keywords))

def test_build_keywords():
    assert build_keywords(["foo", "bar"]) == "(foo OR bar)"
    assert build_keywords(["foo"]) == "foo"
    assert build_keywords(None) == ""

@lru_cache(1000)
def find_submissions(target: Seed, num_results=10):
    # Optimization notes:
    # Quoting the company is helpful to require that in the results BUT if the company name has Inc or something on it, it'll decrease recall
    # Related: this was a slight improvement in testing (maybe 10% better recall)
    # Additional keywords: this was a massive improvement in testing, but relies on manual curation of those keywords
    query = f'site:reddit.com "{target.company}" related:{target.domain} {build_keywords(target.keywords)}'
    if target.product != target.company:
        query += f' "{target.product}"'

    return list(
        result
        for result in search(query, num=num_results)
        if REDDIT_COMMENTS_URL_PATTERN.match(result.link)
    )
