from datetime import datetime, timedelta
import requests
from search import search
from core import CompanyProduct, cache
import re
from typing import Iterable, List, Optional
from pydantic import BaseModel


def find_steam_page(target: CompanyProduct) -> str:
    """Find the Steam page for a company using Google search"""
    result = next(
        search(
            f'site:store.steampowered.com/app/ "{target.company}" "{target.product}"',
            num=1,
        )
    )

    return result.link


STEAM_URL_PATTERN = re.compile(r"https://store.steampowered.com/app/(\d+)/(\w+)/")


def extract_steam_id(url: str) -> Optional[int]:
    if STEAM_URL_PATTERN.match(url):
        return int(STEAM_URL_PATTERN.match(url).group(1))
    return None


def test_extract_steam_id():
    assert (
        extract_steam_id("https://store.steampowered.com/app/2707930/Palia/") == 2707930
    )
    assert extract_steam_id("https://www.google.com") == None


class Author(BaseModel):
    last_played: int
    num_games_owned: int
    num_reviews: int
    playtime_at_review: int
    playtime_forever: int
    playtime_last_two_weeks: int
    steamid: str


class SteamReview(BaseModel):
    author: Author
    comment_count: int
    hidden_in_steam_china: bool
    language: str
    received_for_free: bool
    recommendationid: str
    review: str
    steam_china_location: str
    steam_purchase: bool
    timestamp_created: int
    timestamp_updated: int
    voted_up: bool
    votes_funny: int
    votes_up: int
    weighted_vote_score: float
    written_during_early_access: bool

    developer_response: Optional[str] = None
    timestamp_dev_responded: Optional[int] = None


class QuerySummary(BaseModel):
    num_reviews: int

    # These are only on the first page
    review_score: Optional[int] = None
    review_score_desc: Optional[str] = None
    total_positive: Optional[int] = None
    total_negative: Optional[int] = None
    total_reviews: Optional[int] = None


class SteamResponse(BaseModel):
    cursor: str
    query_summary: QuerySummary
    reviews: List[SteamReview]
    success: int


def iter_reviews(steam_id: int, num_reviews=100) -> Iterable[SteamReview]:
    num_per_page = 100 if num_reviews > 100 else num_reviews

    reviews_collected = 0
    cursor = "*"

    while reviews_collected < num_reviews:
        response = requests.get(
            f"https://store.steampowered.com/appreviews/{steam_id}",
            params={
                "json": 1,
                "language": "english",
                "purchase_type": "all",
                "num_per_page": num_per_page,
                "cursor": cursor,
                # "filter": "recent",
                # "review_type": "all",
                # "cursor": "*",
                # "day_range": 365,
                # "filter_offtopic_activity": 0
            },
        )
        response.raise_for_status()

        response_data = SteamResponse(**response.json())

        # Nothing to emit
        if not response_data.success or not response_data.reviews:
            break

        yield from response_data.reviews

        # We got partial results, which is a sign it's the last page
        if response_data.query_summary.num_reviews < num_per_page:
            break

        cursor = response_data.cursor

    return response_data.reviews


@cache.memoize(expire=timedelta(days=1).total_seconds(), tag="steam")
def get_reviews(steam_id: int, num_reviews=100) -> List[SteamReview]:
    return list(iter_reviews(steam_id, num_reviews))


def review_to_markdown(review: SteamReview) -> str:
    review_dt = datetime.fromtimestamp(review.timestamp_created)
    return f"""
# {'Thumbs Up' if review.voted_up else 'Thumbs Down'} ({review.author.steamid}, Steam, {review_dt.strftime('%Y-%m-%d')})
{review.review.strip()}
""".strip()
