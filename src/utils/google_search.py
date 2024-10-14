from googleapiclient.discovery import build
import os
from typing import Iterable, Optional
from pydantic import BaseModel
from loguru import logger
from urllib.parse import urlencode

_service = build("customsearch", "v1", developerKey=os.getenv("GOOGLE_API_KEY"))


class SearchResult(BaseModel):
    """Google search result"""
    title: str
    link: str
    snippet: Optional[str] = None
    formattedUrl: str


def search(
    query: str, dateRestrict=None, linkSite=None, num: int = 10
) -> Iterable[SearchResult]:
    """
    Wrapper for the Google Custom Search API to add parameters, types, and authentication with defaults that are appropriate for this project.

    Args:
        query (str): The search query.
        dateRestrict (str, optional): Restricts results to URLs based on date. Possible values are: d[number], w[number], m[number], y[number]. For example, d10 returns URLs indexed by Google in the past 10 days. Defaults to None.
        linkSite (str, optional): Restricts results to URLs from a specified site. Defaults to None.
        num (int, optional): Number of search results to return. Defaults to 10.
    """

    assert num <= 100, "Google Custom Search API only allows up to 100 results per query"

    kwargs = {}
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
            yield SearchResult(**result)


def filter_url(search_iter: Iterable[SearchResult], url_substring: str) -> Iterable[SearchResult]:
    """Filter search results by URL substring"""
    for result in search_iter:
        if url_substring in result.link:
            yield result


def filter_title_relevance(search_iter: Iterable[SearchResult], query: str, min_unigram_ratio=0.5) -> Iterable[SearchResult]:
    """Filter search results by unigram overlap between the title and the query"""
    query_unigrams = set(query.split())
    for result in search_iter:
        title_unigrams = set(result.title.split())
        if len(title_unigrams & query_unigrams) / len(query_unigrams) > min_unigram_ratio:
            yield result

def url_from_query(query: str) -> str:
    query_params = {"q": query}
    encoded_query = urlencode(query_params)
    return f"https://www.google.com/search?{encoded_query}"

def test_url_from_query():
    assert url_from_query("foo bar") == "https://www.google.com/search?q=foo+bar"
    assert url_from_query("foo") == "https://www.google.com/search?q=foo"