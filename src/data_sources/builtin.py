"""
Module for scraping the BuiltIn website for company information
"""

from utils.scrape import request_article
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
import re
import pandas as pd
from loguru import logger


def parse_companies(html: str) -> List[Dict[str, str]]:
    """Extract company information from a company list page such as https://www.builtinseattle.com/companies"""
    soup = BeautifulSoup(html, "html.parser")

    company_list_section = soup.select_one("#main-container")

    company_rows = company_list_section.select("div.company-unbounded-responsive")

    companies = []
    for row in company_rows:
        name_tag = row.select_one(
            "div:nth-of-type(2) > div:nth-of-type(1) > a:nth-of-type(2) > h2"
        )
        name = name_tag.text.strip()
        link = name_tag.find_parent("a")["href"]
        description = row.select_one("div:nth-of-type(2) > p").text.strip()

        industry_tag = row.select_one("div:nth-of-type(2) > div:nth-of-type(2)")
        industry = industry_tag.text.strip() if industry_tag else "N/A"

        size_tag = row.select_one(
            "div:nth-of-type(2) > div:nth-of-type(3) > div:nth-of-type(2) > span"
        )
        size = size_tag.text.strip() if size_tag else "N/A"

        # TODO: Pydantic model
        companies.append(
            {
                "name": name,
                "description": description,
                "link": link,
                "industry": industry,
                "size": size,
            }
        )

    return companies


def clean_text(text: str) -> str:
    """
    Clean up text by removing extra spaces and newlines. Needed for formatting the number of employees
    """
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def extract_optional_text(element) -> Optional[str]:
    """
    Extract text from an element if it exists, otherwise return None
    """
    return clean_text(element.text) if element else None


def parse_company_details(html: str) -> Dict[str, str]:
    """
    Extract company details from a company page such as https://www.builtinseattle.com/company/convoy
    """
    soup = BeautifulSoup(html, "html.parser")

    # The header part with the name
    name = soup.select_one("div.card-head > h1").text.strip()

    # The grid part with basic company info
    # Note that the number of entries is dynamic so that's why we're using :has() to find the right div
    # TODO: local employees: fa-lightbulb-on
    company_info = soup.select_one("div.company-info")

    location = extract_optional_text(
        company_info.select_one("div:has(i.fa-location-dot)")
    )
    employees = extract_optional_text(
        company_info.select_one("div:has(i.fa-user-group)")
    )
    founded = extract_optional_text(company_info.select_one("div:has(i.fa-calendar)"))

    website = company_info.select_one("div:has(i.fa-arrow-up-right-from-square) > a")[
        "href"
    ].strip()

    hiring_card = soup.select_one("#we-are-hiring")
    hiring_by_category = {}

    if hiring_card:
        for category_row in hiring_card.select("a"):
            try:
                category_name = category_row.select_one(
                    "span:nth-of-type(1)"
                ).text.strip()
                num_roles = category_row.select_one(
                    "span:nth-of-type(2) > b"
                ).text.strip()
                link = category_row["href"]

                hiring_by_category[category_name] = {
                    "num_roles": num_roles,
                    "link": link,
                }
            except AttributeError:
                # Links that don't have the span structure in there
                continue

    # Info that isn't parsed:
    # The description from the top and industries
    # The benefits section (note: It's shortened on the main page, need to go to another page to get the full list)

    return {
        "name": name,
        "location": location,
        "employees": employees,
        "founded": founded,
        "website": website,
        "hiring_by_category": hiring_by_category,
    }


def scrape(city: str, num_pages: int) -> pd.DataFrame:
    base = f"https://www.builtin{city}.com"

    companies_from_list = []
    companies_from_pages = []

    for page in range(1, num_pages + 1):
        url = (
            f"{base}/companies"
            if page == 1
            else f"{base}/companies?country=USA&page={page}"
        )

        logger.info(f"Fetching company list from {url}")
        response = request_article(url)
        if not response or not response.ok:
            logger.warning(f"Failed to fetch page {page}: {response.status_code}")
            break

        companies = parse_companies(response.content)
        companies_from_list.extend(companies)

        for company in companies:
            company_url = f"{base}{company['link']}"

            logger.info(
                f"Fetching company details for {company['name']} from {company_url}"
            )
            detail_response = request_article(company_url)
            if not detail_response or not detail_response.ok:
                logger.warning(
                    f"Failed to fetch company details for {company['name']}: {detail_response.status_code}"
                )
                continue

            company_html = detail_response.content
            company_details = parse_company_details(company_html)

            companies_from_pages.append(company_details)

    # TODO: Pandas feels like overkill for this; refactor in the future
    overviews = (
        pd.DataFrame(companies_from_list)
        .drop_duplicates(subset="name")
        .set_index("name")
    )
    details = (
        pd.DataFrame(companies_from_pages)
        .drop_duplicates(subset="name")
        .set_index("name")
    )

    company_df = overviews.join(details, how="inner")

    return company_df
