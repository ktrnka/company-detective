from pprint import pprint
from search import search
from core import CompanyProduct
import scrapfly_scrapers.crunchbase
import jinja2
from datetime import datetime
from .models import *

from loguru import logger

scrapfly_scrapers.crunchbase.BASE_CONFIG["cache"] = True
templates = jinja2.Environment(loader=jinja2.FileSystemLoader("templates"))

_response_cache = {}


def find_people_url(target: CompanyProduct) -> str:
    """Find the Crunchbase people page for a company using Google search"""
    result = next(
        search(f'site:www.crunchbase.com/organization "{target.company}"', num=1)
    )
    assert "/organization/" in result.link

    return f"{result.link}/people"


async def run(target: CompanyProduct, debug=False) -> str:
    """
    Run the Crunchbase pipeline:
    1. Find the Crunchbase people page for the company
    2. Scrape the page
    3. Parse the response
    4. Format the response as markdown
    """
    url = find_people_url(target)

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
