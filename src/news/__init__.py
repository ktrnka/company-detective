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
    article_markdowns: Mapping[str, str]

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

    article_markdowns = {result.link: news.scrape.get_article_markdown(result.link) for result in search_results}

    article_markdown_list = [article for article in article_markdowns.values() if article]

    llm_result = news.summarize.summarize(target, article_markdown_list)

    return NewsSummary(
        target=target, 
        search_results=search_results, 
        article_markdowns=article_markdowns, 
        summary_markdown=llm_result.content
        )

