import requests
from bs4 import BeautifulSoup
from typing import Optional
import time

import requests_cache.models.response
from bs4 import BeautifulSoup

# NOTE: This is newpaper4k not newspaper3k
import newspaper
from loguru import logger

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
            time.sleep(delay_seconds)

        return response
    except requests.exceptions.ReadTimeout as e:
        logger.warning(f"Timeout on {url}")
        return None
    except requests.exceptions.SSLError as e:
        logger.warning(f"SSL error on {url}")
        return None
    except requests.exceptions.ConnectionError as e:
        logger.warning(f"Connection error on {url}, usually this means max retries exceeded")
        return None
    except requests.exceptions.ChunkedEncodingError as e:
        logger.warning(f"Chunked encoding error on {url}")
        return None


def remove_img_tags(html_str: str) -> str:
    """Remove all img tags from an HTML string"""
    soup = BeautifulSoup(html_str, "html.parser")
    for img in soup.find_all("img"):
        img.decompose()
    return str(soup)


def response_to_article(
    response: requests_cache.models.response.BaseResponse,
) -> newspaper.Article:
    """Parse the response from a URL into a newspaper Article"""
    article = newspaper.article(
        response.url,
        language="en",
        # Remove images to prevent downloading them, which crashes
        input_html=remove_img_tags(response.text),
        fetch_images=False,
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
