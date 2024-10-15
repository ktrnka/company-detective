from scrapfly import ScrapflyAspError, ScrapflyScrapeError
from google_search import filter_title_relevance, filter_url, search
from core import Seed, cache
import scrapfly_scrapers.crunchbase
import jinja2
from datetime import datetime, timedelta
from .models import *

from loguru import logger

# CONFIGURE SCRAPFLY
scrapfly_scrapers.crunchbase.BASE_CONFIG["cache"] = True

# Cost budget to allow ASP to automatically tweak things to get a response
scrapfly_scrapers.crunchbase.BASE_CONFIG["cost_budget"] = 50


templates = jinja2.Environment(loader=jinja2.FileSystemLoader("templates"))


def find_people_url(target: Seed) -> Optional[str]:
    """Find the Crunchbase people page for a company using Google search"""

    results_iter = search(f'site:www.crunchbase.com/organization "{target.company}"', num=10)
    results_iter = filter_url(results_iter, "/organization/")
    results_iter = filter_title_relevance(results_iter, target.company)
    
    results = list(results_iter)

    if not results:
        return None

    return f"{results[0].link}/people"


async def run(target: Seed) -> Optional[str]:
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

    crunchbase_raw_response = cache.get(url)
    if not crunchbase_raw_response:
        try:
            crunchbase_raw_response = await scrapfly_scrapers.crunchbase.scrape_company(url)
            cache.set(url, crunchbase_raw_response, expire=timedelta(days=14).total_seconds())

            logger.debug("Updating cache with Crunchbase response: {}", crunchbase_raw_response)
        except ScrapflyAspError as e:
            logger.warning("Failed to process Crunchbase (ScrapflyAspError), skipping: {}", e)
            return None
        except ScrapflyScrapeError as e:
            logger.warning("Failed to process Crunchbase (ScrapflyScrapeError), skipping: {}", e)
            return None

    organization, employees = parse(crunchbase_raw_response)

    return templates.get_template("crunchbase.md").render(
        organization=organization, employees=employees, current_year=datetime.now().year
    )
