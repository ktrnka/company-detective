from googleapiclient.discovery import build
import os
from typing import Iterable, Optional
from pydantic import BaseModel
from loguru import logger
from urllib.parse import urlencode

from core import tokenize

_service = build("customsearch", "v1", developerKey=os.getenv("GOOGLE_API_KEY"))


class SearchResult(BaseModel):
    """Google search result"""
    title: str
    link: str
    snippet: Optional[str] = None
    formattedUrl: str


def search(
    query: str, dateRestrict=None, linkSite=None, num: int = 10, drop_duplicates=True
) -> Iterable[SearchResult]:
    """
    Wrapper for the Google Custom Search API to add parameters, types, and authentication with defaults that are appropriate for this project.

    Args:
        query (str): The search query.
        dateRestrict (str, optional): Restricts results to URLs based on date. Possible values are: d[number], w[number], m[number], y[number]. For example, d10 returns URLs indexed by Google in the past 10 days. Defaults to None.
        linkSite (str, optional): Restricts results to URLs from a specified site. Defaults to None.
        num (int, optional): Number of search results to return. Defaults to 10.
        drop_duplicates (bool, optional): Whether to drop duplicate URLs. Defaults to True.
    """

    assert num <= 100, "Google Custom Search API only allows up to 100 results per query"

    kwargs = {}
    urls_yielded = set()
    if dateRestrict:
        kwargs["dateRestrict"] = dateRestrict
    if linkSite:
        kwargs["linkSite"] = linkSite

    for start in range(0, num, 10):
        # https://developers.google.com/custom-search/v1/reference/rest/v1/cse/list
        # fileType is another to consider
        results = (
            _service.cse()
            .list(
                q=query,
                cx=os.getenv("GOOGLE_CSE_ID"),
                num=min(10, num - start),
                # Note: Indexing is 1-based. I found it was more comfortable to stay 0-based until this line
                start=start + 1,
                # defaults for search quality enUS
                lr="lang_en",
                hl="en",
                gl="us",
                **kwargs,
            )
            .execute()
        )

        logger.debug("Google search results: {}", results)

        if results["searchInformation"]["totalResults"] == "0":
            break

        for result in results["items"]:
            if not (drop_duplicates and result["link"] in urls_yielded):
                yield SearchResult(**result)
                urls_yielded.add(result["link"])


def filter_url(search_iter: Iterable[SearchResult], url_substring: str) -> Iterable[SearchResult]:
    """Filter search results by URL substring"""
    for result in search_iter:
        if url_substring in result.link:
            yield result


def filter_title_relevance(search_iter: Iterable[SearchResult], query: str, min_unigram_ratio=0.5) -> Iterable[SearchResult]:
    """Filter search results by unigram overlap between the title and the query"""
    query_unigrams = set(tokenize(query))
    for result in search_iter:
        title_unigrams = set(tokenize(result.title))
        if len(title_unigrams & query_unigrams) / len(query_unigrams) > min_unigram_ratio:
            yield result

def test_filter_title_relevance():
    # A basic test
    search_results = [
        SearchResult(title="foo bar", link="https://example.com", formattedUrl="example.com"),
        SearchResult(title="foo", link="https://example.com", formattedUrl="example.com"),
    ]
    filtered = list(filter_title_relevance(search_results, "foo"))
    assert len(filtered) == 2

    # A test of a failure
    page_title = "GE Current, a Daintree Company"
    query = "Current"

    search_results = [
        SearchResult(title=page_title, link="https://example.com", formattedUrl="example.com"),
    ]
    filtered = list(filter_title_relevance(search_results, query))
    assert len(filtered) == 1

def url_from_query(query: str) -> str:
    query_params = {"q": query}
    encoded_query = urlencode(query_params)
    return f"https://www.google.com/search?{encoded_query}"

def test_url_from_query():
    assert url_from_query("foo bar") == "https://www.google.com/search?q=foo+bar"
    assert url_from_query("foo") == "https://www.google.com/search?q=foo"