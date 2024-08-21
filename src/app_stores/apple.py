from datetime import timedelta
from search import search
from core import CompanyProduct, cache
import re
from typing import Optional, List

from app_store_web_scraper import AppStoreEntry, AppReview


def find_app_store_page(target: CompanyProduct) -> str:
    result = next(
        search(f'site:apps.apple.com "{target.company}" "{target.product}"', num=1)
    )
    assert "/app/" in result.link

    return result.link


def extract_apple_app_store_id(url: str) -> Optional[int]:
    """Get the Apple App Store ID from an app store URL, or return None if not found."""
    pattern = r"https://apps.apple.com/us/app/[^/]+/id(\d+)"
    match = re.search(pattern, url)
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
# {review.title}, {review.rating} stars ({review.user_name}, Apple App Store, {review.date.strftime("%Y-%m-%d")})
{review.content}
""".strip()
