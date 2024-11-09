from scrapfly import ScrapflyError
from utils.google_search import filter_title_relevance, filter_url, search
from core import Seed, cache
import jinja2
from datetime import datetime, timedelta

from .models import *
from .scrapfly_scraper import scrape_company

from loguru import logger

templates = jinja2.Environment(loader=jinja2.FileSystemLoader("templates"))


def find_url(target: Seed) -> Optional[str]:
    """Find the Crunchbase people page for a company using Google search"""

    results_iter = search(
        f"site:www.crunchbase.com/organization {target.company} {target.domain}", num=10
    )
    results_iter = filter_url(results_iter, "/organization/")
    results_iter = filter_title_relevance(results_iter, target.company)

    results = list(results_iter)

    if not results:
        return None

    return results[0].link


async def run(target: Seed) -> Optional[str]:
    """
    Run the Crunchbase pipeline:
    1. Find the Crunchbase page for the company
    2. Scrape the page
    3. Parse the response
    4. Format the response as markdown
    """
    url = find_url(target)
    if not url:
        return None

    crunchbase_raw_response = cache.get(url)
    if not crunchbase_raw_response:
        try:
            crunchbase_raw_response = await scrape_company(url)
            if not crunchbase_raw_response:
                return None

            # TODO: Scrapfly caches for 1 week max, but this info is pretty static so we could cache much longer
            cache.set(
                url, crunchbase_raw_response, expire=timedelta(days=14).total_seconds()
            )

            logger.debug(
                "Updating cache with Crunchbase response: {}", crunchbase_raw_response
            )
        except ScrapflyError as e:
            logger.warning("Failed to process Crunchbase, skipping: {}", e)
            return None

    organization = Organization(**crunchbase_raw_response)

    return templates.get_template("crunchbase.md").render(
        organization=organization, current_year=datetime.now().year
    )
