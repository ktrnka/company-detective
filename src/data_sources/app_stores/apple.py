from datetime import timedelta

from loguru import logger
from utils.google_search import search
from core import Seed, cache
import re
from typing import Optional, List

from app_store_web_scraper import AppStoreEntry, AppReview

from .util import synth_url

URL_PATTERN = re.compile(r"https://apps.apple.com/us/app/[^/]+/id(\d+)")

def find_app_store_page(target: Seed) -> str:
    result = next(
        search(f'site:apps.apple.com "{target.company}" "{target.product}"', num=1)
    )
    assert "/app/" in result.link

    return result.link


def extract_apple_app_store_id(url: str) -> Optional[int]:
    """Get the Apple App Store ID from an app store URL, or return None if not found."""
    match = URL_PATTERN.search(url)
    if match:
        return int(match.group(1))
    else:
        return None


def test_extract_apple_app_store_id():
    assert (
        extract_apple_app_store_id(
            "https://apps.apple.com/us/app/98point6/id1157653928"
        )
        == 1157653928
    )
    assert (
        extract_apple_app_store_id(
            "https://www.98point6.com/press_release/98point6-now-available-nationwide/"
        )
        == None
    )


@cache.memoize(expire=timedelta(days=5).total_seconds(), tag="apple")
def scrape(app_store_id: int, country="us") -> List[AppReview]:
    app = AppStoreEntry(app_id=app_store_id, country=country)

    # It's a lazy iterator, so list() is needed
    # Max 500 reviews per country
    reviews = list(app.reviews())

    return reviews


def review_to_markdown(review: AppReview) -> str:
    return f"""
# {review.title}, {review.rating} stars [({review.user_name}, Apple App Store, {review.date.strftime("%Y-%m-%d")})]({synth_url('apple', review.id)})
{review.content}
""".strip()


def run(apple_store_url: str, num_reviews=100) -> str:
    if num_reviews > 500:
        logger.warning("Apple App Store only supports up to 500 reviews, requested {}", num_reviews)

    apple_store_id = extract_apple_app_store_id(apple_store_url)
    apple_reviews = scrape(apple_store_id)

    # Override: Limit to 100 reviews
    apple_reviews = apple_reviews[:num_reviews]

    apple_review_markdowns = [review_to_markdown(review) for review in apple_reviews]
    apple_review_content = "\n\n".join(apple_review_markdowns)

    logger.info(f"{len(apple_review_content):,} chars in {len(apple_reviews)} reviews")

    return apple_review_content
