from bs4 import BeautifulSoup
from scrapfly import (
    ScrapeApiResponse,
    ScrapeConfig,
    ScrapflyClient,
    ScrapflyScrapeError,
    ScrapflyError,
)
import os
from markdownify import markdownify

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
    async def get_job_listings(cls, careers_url: str):
        job_urls = await cls.get_job_urls(careers_url)
        job_responses = await cls.get_job_responses(job_urls)

        return job_responses

    @classmethod
    async def get_job_responses(cls, job_urls):
        job_responses = []

        async for result in SCRAPFLY.concurrent_scrape(
            [ScrapeConfig(url, **BASE_CONFIG) for url in job_urls], concurrency=2
        ):
            if not isinstance(result, ScrapflyScrapeError):
                job_responses.append(result)
            else:
                print(
                    f"failed to scrape {result.api_response.config['url']}, got: {result.message}"
                )

        return job_responses


class Workable(CareerPage):
    url_base = "https://apply.workable.com"

    @classmethod
    async def get_job_urls(cls, careers_url: str):
        response = await SCRAPFLY.async_scrape(ScrapeConfig(careers_url, **BASE_CONFIG))
        soup = BeautifulSoup(response.content, "html.parser")

        job_list_div = soup.find("ul", {"data-ui": "list"})

        # Get all the links that match a pattern like /company/j/27509D233B/ then re-attach the base
        job_links = job_list_div.find_all("a", href=True)
        job_links = [link for link in job_links if "/j/" in link["href"]]
        job_links = [f"{cls.url_base}{job_link['href']}" for job_link in job_links]

        return job_links

    @staticmethod
    def parse_response(response: ScrapeApiResponse):
        soup = BeautifulSoup(response.content, "html.parser")
        element = soup.find("main")
        return {
            "url": response.context["url"],
            "job_description_text": element.text,
            "job_description_html": element.prettify(),
            "job_description_md": markdownify(element.prettify(), heading_style="atx"),
        }


class Ashby(CareerPage):
    url_base = "https://jobs.ashbyhq.com"

    @classmethod
    async def get_job_urls(cls, careers_url: str):
        response = await SCRAPFLY.async_scrape(ScrapeConfig(careers_url, **BASE_CONFIG))
        soup = BeautifulSoup(response.content, "html.parser")

        job_divs = soup.find_all("div", {"class": "ashby-job-posting-brief-list"})
        job_links = []
        for job_div in job_divs:
            job_links.extend(job_div.find_all("a", href=True))

        job_links = [f"{cls.url_base}{job_link['href']}" for job_link in job_links]

        return job_links

    @staticmethod
    def parse_response(response: ScrapeApiResponse):
        soup = BeautifulSoup(response.content, "html.parser")
        element = soup.find("div", {"id": "overview"})
        return {
            "url": response.context["url"],
            "job_description_text": element.text,
            "job_description_html": element.prettify(),
            "job_description_md": markdownify(element.prettify(), heading_style="atx"),
        }


class SmartRecruiters(CareerPage):
    @classmethod
    async def get_job_urls(cls, careers_url: str):
        response = await SCRAPFLY.async_scrape(ScrapeConfig(careers_url, **BASE_CONFIG))
        soup = BeautifulSoup(response.content, "html.parser")

        job_div = soup.find("section", {"id": "st-openings"})
        job_links = job_div.find_all("a", {"class": "link--block"}, href=True)
        job_links = [job_link["href"] for job_link in job_links]

        return job_links

    @staticmethod
    def parse_response(response: ScrapeApiResponse):
        soup = BeautifulSoup(response.content, "html.parser")
        element = soup.find("main")
        return {
            "url": response.context["url"],
            "job_description_text": element.text,
            "job_description_html": element.prettify(),
            "job_description_md": markdownify(element.prettify(), heading_style="atx"),
        }
