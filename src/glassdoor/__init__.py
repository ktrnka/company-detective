from dataclasses import dataclass
from datetime import timedelta
from typing import List, Optional, Union
from loguru import logger
import numpy as np
from scipy import stats


import scrapfly_scrapers.glassdoor
from scrapfly_scrapers.glassdoor import scrape_reviews, scrape_jobs

from core import Seed, cache
from google_search import SearchResult, search


from glassdoor.summarizer import summarize
from glassdoor.models import UrlBuilder, GlassdoorReview, GlassdoorJob, EmployerKey


scrapfly_scrapers.glassdoor.BASE_CONFIG["cache"] = True


@dataclass
class GlassdoorResult:
    # inputs
    company: Seed

    # intermediate data
    review_page: Union[str, SearchResult]
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
    def empty_result(cls, company: Seed):
        return cls(company, None, {}, [], [], "")


def find_glassdoor_employer(target: Seed) -> Optional[EmployerKey]:
    query = f'site:www.glassdoor.com "{target.company}"'
    urls = list(search(query, num=10))
    return UrlBuilder.find_employer_key([result.link for result in urls])


async def run(
    target: Seed, max_review_pages=1, max_job_pages=0, langchain_config=None
) -> Optional[GlassdoorResult]:
    employer = find_glassdoor_employer(target)

    # job results, not 100% used yet
    jobs = []
    if max_job_pages > 0:
        job_results = await scrape_jobs(
            UrlBuilder.jobs(*employer), max_pages=max_job_pages
        )
        jobs = [GlassdoorJob(**result) for result in job_results]
        jobs = sorted(jobs, key=lambda job: job.jobTitleText)

    reviews_url = UrlBuilder.reviews(*employer)
    response = cache.get(reviews_url)
    if not response:
        response = await scrape_reviews(reviews_url, max_pages=max_review_pages)
        cache.set(reviews_url, response, expire=timedelta(days=10).total_seconds())

        logger.debug("Glassdoor response: {}", response)

    reviews = GlassdoorReview.parse_reviews(employer.name, response)

    review_summary = summarize(target, reviews, langchain_config)

    # TODO: Pull out allReviewsCount from glassdoor_results
    return GlassdoorResult(
        target, reviews_url, response, reviews, jobs, review_summary.content
    )


def summarize_sampling(result: GlassdoorResult, alpha=0.05) -> str:
    """Summarize the review stats compared to the overall distribution"""
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
