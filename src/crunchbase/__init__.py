from typing import Iterable
from search import SearchResult, search
from core import CompanyProduct
import scrapfly_scrapers.crunchbase
import jinja2
from datetime import datetime
from .models import *

from loguru import logger

scrapfly_scrapers.crunchbase.BASE_CONFIG["cache"] = True
templates = jinja2.Environment(loader=jinja2.FileSystemLoader("templates"))

_response_cache = {}


def filter_url(search_iter: Iterable[SearchResult], url_substring: str) -> Iterable[SearchResult]:
    """Filter search results by URL substring"""
    for result in search_iter:
        if url_substring in result.link:
            yield result

def filter_title_relevance(search_iter: Iterable[SearchResult], query: str, min_unigram_ratio=0.5) -> Iterable[SearchResult]:
    """Filter search results by unigram overlap between the title and the query"""
    query_unigrams = set(query.split())
    for result in search_iter:
        title_unigrams = set(result.title.split())
        if len(title_unigrams & query_unigrams) / len(query_unigrams) > min_unigram_ratio:
            yield result

def find_people_url(target: CompanyProduct) -> Optional[str]:
    """Find the Crunchbase people page for a company using Google search"""

    results_iter = search(f'site:www.crunchbase.com/organization "{target.company}"', num=10)
    results_iter = filter_url(results_iter, "/organization/")
    results_iter = filter_title_relevance(results_iter, target.company)
    
    results = list(results_iter)

    if not results:
        return None

    return f"{results[0].link}/people"


async def run(target: CompanyProduct) -> Optional[str]:
    """
    Run the Crunchbase pipeline:
    1. Find the Crunchbase people page for the company
    2. Scrape the page
    3. Parse the response
    4. Format the response as markdown
    """
    url = find_people_url(target)
    if not url:
        return None

    # For whatever reason, Scrapfly doesn't cache all the time
    # TODO: Replace this with a sqlite cache
    if url not in _response_cache:
        _response_cache[url] = await scrapfly_scrapers.crunchbase.scrape_company(url)

    crunchbase_raw_response = _response_cache[url]
    logger.debug("Crunchbase response: {}", crunchbase_raw_response)
    organization, employees = parse(crunchbase_raw_response)

    return templates.get_template("crunchbase.md").render(
        organization=organization, employees=employees, current_year=datetime.now().year
    )
