from datetime import datetime, timedelta
from src.google_search import search
from core import CompanyProduct, cache
from typing import List, Optional
from urllib.parse import urlparse, parse_qs
import google_play_scraper

from pydantic import BaseModel


def find_google_play_page(target: CompanyProduct) -> str:
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


@cache.memoize(expire=timedelta(days=5).total_seconds(), tag="google_play")
def scrape_reviews(app_id: str) -> List[GooglePlayReview]:
    review_data, reviews_continuation_token = google_play_scraper.reviews(
        app_id,
        lang="en",
        country="us",
        sort=google_play_scraper.Sort.NEWEST,
        # TODO: See if there's any sort of throttling on this
        count=100,
    )

    return [GooglePlayReview(**review) for review in review_data]


def review_to_markdown(review: GooglePlayReview) -> str:
    return f"""
# {review.score} stars ({review.userName}, Google Play Store, {review.at.strftime("%Y-%m-%d")})
{review.content}
""".strip()
