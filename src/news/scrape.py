import requests
from bs4 import BeautifulSoup
from functools import lru_cache
from typing import Optional
import time

import requests_cache.models.response


@lru_cache(maxsize=1000)
def get_article_text(url: str, delay_seconds=1) -> Optional[str]:
    """Get the text of an article from a URL"""
    try:
        response = requests.get(
            url,
            timeout=5,
            headers={
                "Accept": "text/html",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            },
        )

        # Very basic rate limiting if the cache wasn't used
        if not isinstance(response, requests_cache.models.response.CachedResponse):
            print(
                f"get_article_text: Cache miss, delaying {delay_seconds} seconds for {url}"
            )
            time.sleep(delay_seconds)
        else:
            print(f"get_article_text: Cache hit for {url}")
    except requests.exceptions.ReadTimeout as e:
        print(f"get_article_text: Timeout on {url}")
        return None

    if response.ok:
        soup = BeautifulSoup(response.text, "html.parser")
        article = soup.find("article")
        if article:
            return article.get_text().strip()
    else:
        print(
            f"get_article_text: Failed to get article from {url}: {response.status_code}"
        )

    return None


def get_article_markdown(url: str) -> Optional[str]:
    """Get the text of an article from a URL with basic Markdown formatting"""
    text = get_article_text(url)
    if text:
        return f"""
# URL: {url}

{text}
"""
    else:
        return None


import newspaper


def request_article(
    url: str, delay_seconds=1
) -> Optional[requests_cache.models.response.BaseResponse]:
    """Handle HTTP request for the URL with caching and rate limiting"""
    try:
        response = requests.get(
            url,
            timeout=5,
            headers={
                "Accept": "text/html",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            },
        )

        # Very basic rate limiting if the cache wasn't used
        if not isinstance(response, requests_cache.models.response.CachedResponse):
            print(
                f"request_article: Cache miss, delaying {delay_seconds} seconds for {url}"
            )
            time.sleep(delay_seconds)
        else:
            print(f"request_article: Cache hit for {url}")

        return response
    except requests.exceptions.ReadTimeout as e:
        print(f"request_article: Timeout on {url}")
        return None


def response_to_article(
    response: requests_cache.models.response.BaseResponse,
) -> newspaper.Article:
    """Parse the response from a URL into a newspaper Article"""
    article = newspaper.article(
        response.url, language="en", input_html=response.text, fetch_images=False
    )
    article.parse()
    return article


def article_to_markdown(article: newspaper.Article, max_chars=None) -> str:
    """Format a parsed newspaper Article into Markdown for summarization"""
    header = article.title
    if article.authors:
        header += f" by {', '.join(article.authors)}"
    if article.publish_date:
        header += f" on {article.publish_date.strftime('%Y-%m-%d')}"

    text = article.text
    if max_chars:
        text = text[:max_chars]

    header = f"# [{header}]({article.url})"

    return f"{header}\n{text}"
