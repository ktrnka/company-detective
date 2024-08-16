from dataclasses import dataclass
from pprint import pprint
from typing import List


import scrapfly_scrapers.glassdoor
from scrapfly_scrapers.glassdoor import scrape_reviews, scrape_jobs

from core import CompanyProduct
from search import SearchResult


from glassdoor.search import find_review
from glassdoor.summarizer import summarize
from glassdoor.models import UrlBuilder, GlassdoorReview, GlassdoorJob


scrapfly_scrapers.glassdoor.BASE_CONFIG["cache"] = True


@dataclass
class GlassdoorResult:
    # inputs
    company: CompanyProduct

    # intermediate data
    review_page: SearchResult
    raw_reviews: dict
    reviews: List[GlassdoorReview]

    # outputs
    jobs: List[GlassdoorJob]
    summary_markdown: str

    @property
    def num_parsed_reviews(self):
        return len(self.reviews)

    @property
    def num_raw_reviews(self):
        return self.raw_reviews.get("allReviewsCount", 0)


async def run(
    target: CompanyProduct, max_review_pages=1, max_job_pages=0, debug=False, url_override=None
) -> GlassdoorResult:
    
    # NOTE: This is necessary in rare cases where the Google search results don't contain the overview page at all, like Pomelo Care
    if url_override:
        review_page = SearchResult(
            link=url_override,
            formattedUrl=url_override,
            title="Manually-entered Glassdoor URL",)
    else:
        review_page = find_review(target, debug=debug)
    company, company_id = UrlBuilder.parse_review_url(review_page.link)

    # job results, not 100% used yet
    jobs = []
    if max_job_pages > 0:
        job_results = await scrape_jobs(
            UrlBuilder.jobs(company, company_id), max_pages=max_job_pages
        )
        jobs = [GlassdoorJob(**result) for result in job_results]
        jobs = sorted(jobs, key=lambda job: job.jobTitleText)

    response = await scrape_reviews(review_page.link, max_pages=max_review_pages)

    if debug:
        pprint(response)
    reviews = GlassdoorReview.parse_reviews(company, response)

    review_summary = summarize(target, reviews)

    # TODO: Pull out allReviewsCount from glassdoor_results
    return GlassdoorResult(
        target, review_page, response, reviews, jobs, review_summary.content
    )
