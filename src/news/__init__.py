from typing import NamedTuple, Mapping, List

from core import CompanyProduct
from search import SearchResult

import news.search
import news.scrape
import news.summarize

class NewsSummary(NamedTuple):
    # input
    target: CompanyProduct

    # intermediates
    search_results: List[SearchResult]
    article_markdowns: List[str]

    # output
    summary_markdown: str


def run(target: CompanyProduct, max_results=30) -> NewsSummary:
    """
    Run the News pipeline:
    1. Find news articles
    2. Download the articles
    3. Extract the core content as text
    4. Summarize the articles 
    """
    search_results = news.search.find_news_articles(target, num_results=max_results)

    # Fetch and filter
    responses = [news.scrape.request_article(result.link) for result in search_results]
    responses = [response for response in responses if response.ok]

    # Parse and format
    articles = [news.scrape.response_to_article(response) for response in responses]
    article_markdowns = [news.scrape.article_to_markdown(article) for article in articles]

    llm_result = news.summarize.summarize(target, article_markdowns)

    return NewsSummary(
        target=target, 
        search_results=search_results, 
        article_markdowns=article_markdowns, 
        summary_markdown=llm_result.content
        )

