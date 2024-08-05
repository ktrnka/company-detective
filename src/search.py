from dotenv import load_dotenv
from googleapiclient.discovery import build
import os
from typing import Iterable, List, NamedTuple
from pprint import pprint

load_dotenv()
_service = build("customsearch", "v1", developerKey=os.getenv("GOOGLE_API_KEY"))


class SearchResult(NamedTuple):
    """Convenience class to represent a search result."""

    title: str
    link: str
    snippet: str
    formattedUrl: str

    @classmethod
    def from_json(cls, json):
        return cls(
            title=json["title"],
            link=json["link"],
            snippet=json["snippet"],
            formattedUrl=json["formattedUrl"],
        )


def search(
    query: str, dateRestrict=None, linkSite=None, num: int = 10, debug=False
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
        results = (
            _service.cse()
            .list(
                q=query,
                cx=os.getenv("GOOGLE_CSE_ID"),
                num=min(10, num - start),
                start=start,
                # defaults for search quality enUS
                lr="lang_en",
                hl="en",
                gl="us",
                **kwargs,
            )
            .execute()
        )

        if debug:
            pprint(results)

        if results["searchInformation"]["totalResults"] == "0":
            break

        for result in results["items"]:
            yield SearchResult.from_json(result)
