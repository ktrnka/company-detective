from typing import NamedTuple, List, Optional
from loguru import logger

from core import Seed
from utils.debug import log_runtime
from utils.google_search import SearchResult
from utils.scrape import response_to_article, article_to_markdown
from utils.async_scrape import scrape

from .search import find_news_articles
from .summarize import summarize

class NewsSummary(NamedTuple):
    # input
    target: Seed

    # intermediates
    search_results: List[SearchResult]
    article_markdowns: List[str]

    # output
    summary_markdown: str


async def run(target: Seed, max_results=30, langchain_config=None) -> Optional[NewsSummary]:
    """
    Run the News pipeline:
    1. Find news articles
    2. Download the articles
    3. Extract the core content as text
    4. Summarize the articles 
    """
    with log_runtime("search"):
        search_results = find_news_articles(target, num_results=max_results)

    # Fetch and filter
    with log_runtime("scrape"):
        responses = await scrape([result.link for result in search_results])
        responses = [response for response in responses if response and response.ok and response.text]

        if target.require_news_backlinks:
            num_before = len(responses)
            responses = [response for response in responses if target.domain in response.text]
            num_after = len(responses)

            logger.info(f"Filtered {num_before - num_after} / {num_before} articles without backlinks")

    # This typically can happen for small companies if we're requiring backlinks
    if not responses:
        logger.warning("No articles found")
        return None

    with log_runtime("parse"):
        # Parse and format
        articles = [response_to_article(response) for response in responses]
        article_markdowns = [article_to_markdown(article) for article in articles]

    with log_runtime("summarize"):
        llm_result = summarize(target, article_markdowns, langchain_config)

    return NewsSummary(
        target=target, 
        search_results=search_results, 
        article_markdowns=article_markdowns, 
        summary_markdown=llm_result.content
        )

