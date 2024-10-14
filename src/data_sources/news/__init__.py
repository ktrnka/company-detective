from typing import NamedTuple, List

from core import Seed
from utils.debug import log_runtime
from utils.google_search import SearchResult
from utils.scrape import request_article, response_to_article, article_to_markdown

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


def run(target: Seed, max_results=30, langchain_config=None) -> NewsSummary:
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
        responses = [request_article(result.link) for result in search_results]
        responses = [response for response in responses if response and response.ok]

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

