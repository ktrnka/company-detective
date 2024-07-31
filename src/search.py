from dotenv import load_dotenv
from googleapiclient.discovery import build
import os
from typing import List, NamedTuple

load_dotenv()
_service = build(
    "customsearch", "v1", developerKey=os.getenv("GOOGLE_API_KEY")
)

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

def search(query: str, dateRestrict=None, linkSite=None, num: int=10) -> List[SearchResult]:
    """
    Wrapper for the Google Custom Search API to add parameters, types, and authentication with defaults that are appropriate for this project.
    
    Args:
        query (str): The search query.
        dateRestrict (str, optional): Restricts results to URLs based on date. Possible values are: d[number], w[number], m[number], y[number]. For example, d10 returns URLs indexed by Google in the past 10 days. Defaults to None.
        linkSite (str, optional): Restricts results to URLs from a specified site. Defaults to None.
    """

    kwargs = {}
    if dateRestrict:
        kwargs["dateRestrict"] = dateRestrict
    if linkSite:
        kwargs["linkSite"] = linkSite

    # https://developers.google.com/custom-search/v1/reference/rest/v1/cse/list
    res = (
        _service.cse()
        .list(
            q=query,
            cx=os.getenv("GOOGLE_CSE_ID"),
            num=num,
            # defaults for search quality enUS
            lr="lang_en",
            hl="en",
            gl="us",
            **kwargs,
        )
        .execute()
    )
    return [SearchResult.from_json(item) for item in res["items"]]

