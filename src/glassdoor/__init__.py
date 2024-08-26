from dataclasses import dataclass
from typing import List, Optional
from loguru import logger
import numpy as np
from scipy import stats


import scrapfly_scrapers.glassdoor
from scrapfly_scrapers.glassdoor import scrape_reviews, scrape_jobs

from core import CompanyProduct
from google_search import SearchResult


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
    
    @classmethod
    def empty_result(cls, company: CompanyProduct):
        return cls(company, None, {}, [], [], "")


async def run(
    target: CompanyProduct, max_review_pages=1, max_job_pages=0, url_override=None
) -> Optional[GlassdoorResult]:

    # NOTE: This is necessary in rare cases where the Google search results don't contain the overview page at all, like Pomelo Care
    if url_override:
        review_page = SearchResult(
            link=url_override,
            formattedUrl=url_override,
            title="Manually-entered Glassdoor URL",
        )
    else:
        review_page = find_review(target)

        # If we don't find a review page, return None
        if not review_page:
            logger.warning("No Glassdoor review page found for {}", target)
            return None

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

    logger.debug("Glassdoor response: {}", response)

    reviews = GlassdoorReview.parse_reviews(company, response)

    review_summary = summarize(target, reviews)

    # TODO: Pull out allReviewsCount from glassdoor_results
    return GlassdoorResult(
        target, review_page, response, reviews, jobs, review_summary.content
    )



def summarize_sampling(result: GlassdoorResult, alpha=0.05) -> str:
    sample_scores = np.array([review.ratingOverall for review in result.reviews])
    population_mean = result.raw_reviews["ratings"]["overallRating"]
    t_statistic, p_value = stats.ttest_1samp(sample_scores, population_mean)
    min_date = min(review.reviewDateTime for review in result.reviews)
    max_date = max(review.reviewDateTime for review in result.reviews)
    return f"""
Overall stats
Mean: {population_mean}
Count: {result.raw_reviews["ratings"]["reviewCount"]}
      
Sample stats
Mean: {sample_scores.mean()}
Count: {len(sample_scores)}
Date range: {min_date.strftime('%Y-%m-%d')} to {max_date.strftime('%Y-%m-%d')}

Sample reliability
T-statistic: {t_statistic:.3f}
P-value: {p_value:.3f}
{"Sample is significantly different" if p_value < alpha else "Sample is not significantly different"}
"""
