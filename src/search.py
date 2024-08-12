from dotenv import load_dotenv
from googleapiclient.discovery import build
import os
from typing import Iterable, List, NamedTuple, Optional
from pprint import pprint
from pydantic import BaseModel, model_validator

load_dotenv()
_service = build("customsearch", "v1", developerKey=os.getenv("GOOGLE_API_KEY"))


class SearchResult(BaseModel):
    """Google search result"""
    title: str
    link: str
    snippet: Optional[str]
    formattedUrl: str

    @model_validator(mode='before')
    def _allow_missing_optional(cls, data):
        if "snippet" not in data:
            data["snippet"] = None

        return data


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

        if debug:
            pprint(results)

        if results["searchInformation"]["totalResults"] == "0":
            break

        for result in results["items"]:
            yield SearchResult(**result)
