from datetime import timedelta

from loguru import logger
from utils.collection_cache import CollectionCache
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
    """
    Get the Apple App Store ID from an app store URL, or return None if not found.

    Examples:
    >>> extract_apple_app_store_id("https://apps.apple.com/us/app/98point6/id1157653928")
    1157653928
    >>> extract_apple_app_store_id("https://www.98point6.com/press_release/98point6-now-available-nationwide/") is None
    True
    """
    match = URL_PATTERN.search(url)
    if match:
        return int(match.group(1))
    else:
        return None

def scrape(app_store_id: int, country="us") -> List[AppReview]:
    review_cache = CollectionCache(cache, ttl=timedelta(days=30))
    cache_key = f"apple_reviews:{app_store_id}"

    if cache_key in review_cache and review_cache.get_age(cache_key) < timedelta(days=7):
        reviews = review_cache.get_list(cache_key)
    else:
        app = AppStoreEntry(app_id=app_store_id, country=country)

        # It's a lazy iterator, so list() is needed
        # Max 500 reviews per country
        try:
            # It's lazy so we need to list it
            reviews = list(app.reviews())

            # The cache works in dicts
            reviews = [review.__dict__ for review in reviews]

            review_cache.upsert_list(cache_key, "id", reviews)
        except TypeError as e:
            logger.warning("Failed to fetch Apple App Store reviews, trying to fallback to cache: {}", e)
            reviews = review_cache.get_list(cache_key) or []
    
    # Convert back to AppReview objects
    reviews = [AppReview(**review) for review in reviews]

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
