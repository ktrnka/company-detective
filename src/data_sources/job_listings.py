from bs4 import BeautifulSoup
from scrapfly import (
    ScrapeApiResponse,
    ScrapeConfig,
    ScrapflyClient,
    ScrapflyError,
)
import os
from markdownify import markdownify
from loguru import logger

SCRAPFLY = ScrapflyClient(key=os.environ.get("SCRAPFLY_KEY"))

BASE_CONFIG = {
    "asp": True,
    "render_js": True,
    "country": "us",
    "retry": False,
    # Cache for 1 week (max TTL in Scrapfly)
    "cache": True,
    "cache_ttl": 604800,
    # TO CONSIDER
    # session = value (this will reuse the same machine for subsequent requests due to sticky_proxy, but disables caching)
}


class CareerPage:
    @classmethod
    async def crawl_jobs(cls, careers_url: str):
        job_urls = await cls.scrape_job_links(careers_url)
        job_responses = await cls.scrape_job_descriptions(job_urls)

        return job_responses

    @classmethod
    async def scrape_job_links(cls, careers_url: str):
        raise NotImplementedError

    @classmethod
    async def scrape_job_descriptions(cls, job_urls):
        job_responses = []

        async for result in SCRAPFLY.concurrent_scrape(
            [ScrapeConfig(url, **BASE_CONFIG) for url in job_urls], concurrency=2
        ):
            if not isinstance(result, ScrapflyError):
                job_responses.append(result)
            else:
                logger.warning(
                    f"Failed to scrape {result.api_response.config['url']}, got: {result.message}"
                )

        return job_responses
    
    @classmethod
    def parse_job_response(cls, response: ScrapeApiResponse):
        soup = BeautifulSoup(response.content, "html.parser")
        main_element = cls.find_job_description_element(soup)
        return {
            "url": response.context["url"],
            "job_description_text": main_element.text,
            "job_description_html": main_element.prettify(),
            "job_description_md": markdownify(main_element.prettify(), heading_style="atx"),
        }
    
    @classmethod
    def find_job_description_element(cls, soup):
        raise NotImplementedError


class Workable(CareerPage):
    url_base = "https://apply.workable.com"

    @classmethod
    async def scrape_job_links(cls, careers_url: str):
        response = await SCRAPFLY.async_scrape(ScrapeConfig(careers_url, **BASE_CONFIG))
        soup = BeautifulSoup(response.content, "html.parser")

        job_list_div = soup.find("ul", {"data-ui": "list"})

        # Get all the links that match a pattern like /company/j/27509D233B/ then re-attach the base
        job_links = job_list_div.find_all("a", href=True)
        job_links = [link for link in job_links if "/j/" in link["href"]]
        job_links = [f"{cls.url_base}{job_link['href']}" for job_link in job_links]

        return job_links
    
    @classmethod
    def find_job_description_element(cls, soup):
        return soup.find("main")


class Ashby(CareerPage):
    url_base = "https://jobs.ashbyhq.com"

    @classmethod
    async def scrape_job_links(cls, careers_url: str):
        response = await SCRAPFLY.async_scrape(ScrapeConfig(careers_url, **BASE_CONFIG))
        soup = BeautifulSoup(response.content, "html.parser")

        job_divs = soup.find_all("div", {"class": "ashby-job-posting-brief-list"})
        job_links = []
        for job_div in job_divs:
            job_links.extend(job_div.find_all("a", href=True))

        job_links = [f"{cls.url_base}{job_link['href']}" for job_link in job_links]

        return job_links
    
    @classmethod
    def find_job_description_element(cls, soup):
        return soup.find("div", {"id": "overview"})


class SmartRecruiters(CareerPage):
    @classmethod
    async def scrape_job_links(cls, careers_url: str):
        response = await SCRAPFLY.async_scrape(ScrapeConfig(careers_url, **BASE_CONFIG))
        soup = BeautifulSoup(response.content, "html.parser")

        job_div = soup.find("section", {"id": "st-openings"})
        job_links = job_div.find_all("a", {"class": "link--block"}, href=True)
        job_links = [job_link["href"] for job_link in job_links]

        return job_links
    
    @classmethod
    def find_job_description_element(cls, soup):
        return soup.find("main")
