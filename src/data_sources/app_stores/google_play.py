from datetime import datetime, timedelta

from loguru import logger
from utils.collection_cache import CollectionCache
from utils.google_search import search
from core import Seed, cache
from typing import List, Optional
from urllib.parse import urlparse, parse_qs
import google_play_scraper

from pydantic import BaseModel
import re
import numpy as np
import scipy.stats as stats
from itertools import chain

from .util import synth_url


URL_PATTERN = re.compile(r"https://play.google.com/store/apps/details.*")

def find_google_play_page(target: Seed) -> str:
    result = next(
        search(
            f'site:play.google.com/store/apps/ "{target.company}" "{target.product}"',
            num=1,
        )
    )

    return result.link


def extract_google_play_app_id(url: str) -> Optional[str]:
    """Get the Google Play Store app ID from an app store URL, or return None if not found."""
    parsed_url = urlparse(url)
    if (
        parsed_url.netloc == "play.google.com"
        and parsed_url.path == "/store/apps/details"
    ):
        query_params = parse_qs(parsed_url.query)
        app_id = query_params.get("id")
        if app_id:
            return app_id[0]
    return None


def test_extract_google_play_app_id():
    assert (
        extract_google_play_app_id(
            "https://play.google.com/store/apps/details?id=com.ninety8point6.patientapp&hl=en_US"
        )
        == "com.ninety8point6.patientapp"
    )
    assert (
        extract_google_play_app_id(
            "https://www.98point6.com/press_release/98point6-now-available-nationwide/"
        )
        == None
    )


class Category(BaseModel):
    id: Optional[str]
    name: str


class GooglePlayAppInfo(BaseModel):
    adSupported: bool
    appId: str
    categories: List[Category]
    comments: List[str]
    containsAds: bool
    contentRating: str
    contentRatingDescription: Optional[str]
    currency: str
    description: str
    descriptionHTML: str
    developer: str
    developerAddress: Optional[str]
    developerEmail: str
    developerId: str
    developerWebsite: str
    free: bool
    genre: str
    genreId: str
    headerImage: str
    histogram: List[int]
    icon: str
    inAppProductPrice: Optional[str]
    installs: str
    lastUpdatedOn: str
    minInstalls: int
    offersIAP: bool
    originalPrice: Optional[str]
    price: int
    privacyPolicy: str
    ratings: int
    realInstalls: int
    released: str
    reviews: int
    sale: bool
    saleText: Optional[str]
    saleTime: Optional[str]
    score: float
    screenshots: List[str]
    summary: str
    title: str
    updated: int
    url: str
    version: str
    video: str
    videoImage: str


class GooglePlayReview(BaseModel):
    appVersion: Optional[str]
    at: datetime
    content: str
    repliedAt: Optional[datetime]
    replyContent: Optional[str]
    reviewCreatedVersion: Optional[str]
    reviewId: str
    score: int
    thumbsUpCount: int
    userImage: str
    userName: str


@cache.memoize(expire=timedelta(days=5).total_seconds(), tag="google_play")
def scrape_app_info(app_id: str) -> GooglePlayAppInfo:
    response_data = google_play_scraper.app(app_id, lang="en", country="us")

    return GooglePlayAppInfo(**response_data)


def scrape_reviews(app_id: str, num_reviews=100) -> List[GooglePlayReview]:
    review_cache = CollectionCache(cache, ttl=timedelta(days=14))

    cache_key = f"google_play_reviews:{app_id}"
    if cache_key in review_cache and review_cache.get_age(cache_key) < timedelta(days=7):
        review_data = review_cache.get_list(cache_key)
    else:
        review_data, reviews_continuation_token = google_play_scraper.reviews(
            app_id,
            lang="en",
            country="us",
            sort=google_play_scraper.Sort.NEWEST,
            # The API only supports fetching up to 100 reviews at a time, though possibly more could be done with the continuation token
            count=min(num_reviews, 100),
        )
        review_cache.upsert_list(cache_key, "reviewId", review_data)
        logger.info(f"Upserted {len(review_data)} reviews for {app_id}")

        # The merged and deduplicated list
        review_data = review_cache.get_list(cache_key)

    logger.info(f"Got {len(review_data)} reviews for {app_id}")

    reviews = [GooglePlayReview(**review) for review in review_data]
    if len(reviews) > num_reviews:
        # If the cache has more than requested, sort by date and take the most recent
        reviews = sorted(reviews, key=lambda x: x.at, reverse=True)
        reviews = reviews[:num_reviews]

    return reviews

def review_to_markdown(review: GooglePlayReview) -> str:
    # NOTE: The permalink is fake; it's a placeholder for now
    return f"""
# {review.score} stars [({review.userName}, Google Play Store, {review.at.strftime("%Y-%m-%d")})]({synth_url("google_play", review.reviewId)})
{review.content}
""".strip()


def run(google_play_url: str, num_reviews=100) -> str:
    google_play_id = extract_google_play_app_id(google_play_url)
    google_play_reviews = scrape_reviews(google_play_id, num_reviews)
    google_play_review_markdowns = [review_to_markdown(review) for review in google_play_reviews]
    google_play_review_content = "\n\n".join(google_play_review_markdowns)

    logger.info(f"{len(google_play_review_content):,} chars in {len(google_play_reviews)} reviews")

    return google_play_review_content

def histogram_to_array(histogram):
    return np.asarray(list(chain(*[[num+1] * count for num, count in enumerate(histogram)])))

def summarize_sampling(app_info: GooglePlayAppInfo, reviews: List[GooglePlayReview], alpha=0.05) -> str:
    """Summarize the review stats compared to the overall distribution"""
    sample_scores = np.array([review.score for review in reviews])
    overall_scores = histogram_to_array(app_info.histogram)

    # Perform the two-sample K-S test
    ks_statistic, p_value = stats.ks_2samp(sample_scores, overall_scores)

    # Interpret the results
    if p_value < alpha:
        significance = "significantly different"
    else:
        significance = "not significantly different"

    sample_mean = sum(review.score for review in reviews) / len(reviews)
    reviews_min_date = min(review.at for review in reviews)
    reviews_max_date = max(review.at for review in reviews)

    # date correlation
    sample_dates = np.array([review.at.timestamp() for review in reviews])
    date_score_correlation, date_score_p_value = stats.pearsonr(sample_dates, sample_scores)

    return f"""
# {app_info.title}
{app_info.summary}

Overall
- {app_info.score:.2f}
- {app_info.ratings} ratings
- Approximate date range {app_info.released} to {app_info.lastUpdatedOn}

Sample
- {sample_mean:.2f}
- {len(reviews)} reviews
- Date range {reviews_min_date.strftime('%Y-%m-%d')} to {reviews_max_date.strftime('%Y-%m-%d')}
- Date-score correlation: P={date_score_p_value:.3f}

Sample representativeness
- K-S Statistic: {ks_statistic:.3f}
- p-value: {p_value:.3f}
- The sample distribution is {significance} from the overall distribution
"""

