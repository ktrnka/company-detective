from datetime import datetime, timedelta
from loguru import logger
import requests
from src.utils.google_search import search
from core import Seed, cache
import re
from typing import Iterable, List, Optional
from pydantic import BaseModel
from scipy.stats import chi2_contingency
import numpy as np
from collections import Counter

from .util import synth_url

def find_steam_page(target: Seed) -> str:
    """Find the Steam page for a company using Google search"""
    result = next(
        search(
            f'site:store.steampowered.com/app/ "{target.company}" "{target.product}"',
            num=1,
        )
    )

    return result.link


URL_PATTERN = re.compile(r"https://store.steampowered.com/app/(\d+)/(\w+)/")


def extract_steam_id(url: str) -> Optional[int]:
    if URL_PATTERN.match(url):
        return int(URL_PATTERN.match(url).group(1))
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
    playtime_at_review: Optional[int] = None
    playtime_forever: Optional[int] = None
    playtime_last_two_weeks: Optional[int] = None
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

def get_review_summary_stats(steam_id: int) -> QuerySummary:
    """
    Get the summary statistics for a Steam game by querying the review API for one result and returning the query_summary on the first page of results.
    """
    response = requests.get(
        f"https://store.steampowered.com/appreviews/{steam_id}",
        params={
            "json": 1,
            "language": "english",
            "purchase_type": "all",
            "num_per_page": 1,
        },
    )
    response.raise_for_status()

    response_data = SteamResponse(**response.json())
    return response_data.query_summary

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
        reviews_collected += len(response_data.reviews)

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
# {'Thumbs Up' if review.voted_up else 'Thumbs Down'} [(Anonymous, Steam, {review_dt.strftime('%Y-%m-%d')})]({synth_url("steam", review.author.steamid)})
{review.review.strip()}
""".strip()


def run(steam_url: str, num_reviews=50) -> str:
    steam_reviews = get_reviews(extract_steam_id(steam_url), num_reviews=num_reviews)

    # Override: A previous, cached version didn't use the limit so apply it a second time
    steam_reviews = steam_reviews[:num_reviews]
    steam_review_markdowns = [review_to_markdown(review) for review in steam_reviews]
    steam_review_content = "\n\n".join(steam_review_markdowns)

    logger.info(f"{len(steam_review_content):,} chars in {len(steam_reviews)} reviews")

    return steam_review_content

def summarize_sampling(reviews: List[SteamReview], overall: QuerySummary, alpha=0.05) -> str:
    sample_rating_counts = Counter(review.voted_up for review in reviews)

    # Create a contingency table
    observed = np.array([
        [sample_rating_counts[True], sample_rating_counts[False]],
        [overall.total_positive, overall.total_negative]
    ])

    # Perform the Chi-Square test
    chi2, p_value, dof, expected = chi2_contingency(observed)

    # Interpret the results
    if p_value < alpha:
        significance = "significantly different"
    else:
        significance = "not significantly different"

    min_review_date = min(review.timestamp_created for review in reviews)
    min_review_date = datetime.fromtimestamp(min_review_date)
    max_review_date = max(review.timestamp_created for review in reviews)
    max_review_date = datetime.fromtimestamp(max_review_date)

    return f"""
Overall
- {overall.total_positive / overall.total_reviews:.1%} positive
- Total: {overall.total_reviews}

Sample
- {sample_rating_counts[True] / len(reviews):.1%} positive
- Total: {len(reviews)}
- Date range {min_review_date.strftime('%Y-%m-%d')} to {max_review_date.strftime('%Y-%m-%d')}

Sample representativeness
- Chi-Square Statistic: {chi2:.3f}
- p-value: {p_value:.3f}
- The sample distribution is {significance} from the overall distribution
"""

