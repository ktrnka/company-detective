from dataclasses import dataclass
from datetime import timedelta
from typing import List, Optional, Union
from loguru import logger
import numpy as np
from scipy import stats


from core import Seed, cache
from utils.debug import log_runtime
from utils.google_search import SearchResult, search


from .scrapfly_scraper import scrape_reviews, scrape_jobs
from .summarizer import summarize
from .models import UrlBuilder, GlassdoorReview, GlassdoorJob, EmployerKey


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
    def num_parsed_reviews(self) -> int:
        return len(self.reviews)

    @property
    def num_raw_reviews(self) -> int:
        return self.raw_reviews.get("allReviewsCount", 0)

    @property
    def html_link(self) -> str:
        # Figure out the name from the URL
        link = (
            self.review_page
            if isinstance(self.review_page, str)
            else self.review_page.link
        )
        employer = UrlBuilder.parse_review_url(link)
        # TODO: What to do if it doesn't parse
        formatted_name = employer.name.replace("-", " ").title()

        return f"<a href='{link}'>{formatted_name} on Glassdoor</a>"

    @classmethod
    def empty_result(cls, company: Seed):
        return cls(company, None, {}, [], [], "")


def find_glassdoor_employer(target: Seed) -> Optional[EmployerKey]:
    query = f"site:www.glassdoor.com {target.company} {target.domain}"
    urls = list(search(query, num=10))
    return UrlBuilder.find_employer_key([result.link for result in urls])


async def run(
    target: Seed, max_review_pages=1, max_job_pages=0, langchain_config=None
) -> Optional[GlassdoorResult]:
    with log_runtime("Find employer"):
        employer = find_glassdoor_employer(target)
        if not employer:
            logger.warning("No Glassdoor employer found for {}", target.company)
            return None

    # job results, not 100% used yet
    jobs = []
    if max_job_pages > 0:
        job_results = await scrape_jobs(
            UrlBuilder.jobs(*employer), max_pages=max_job_pages
        )
        jobs = [GlassdoorJob(**result) for result in job_results]
        jobs = sorted(jobs, key=lambda job: job.jobTitleText)

    with log_runtime("Scrape reviews"):
        reviews_url = UrlBuilder.reviews(*employer)
        response = cache.get(reviews_url)
        if not response:
            response = await scrape_reviews(reviews_url, max_pages=max_review_pages)
            cache.set(reviews_url, response, expire=timedelta(days=10).total_seconds())

            logger.debug("Glassdoor response: {}", response)

    with log_runtime("Parse reviews"):
        reviews = GlassdoorReview.parse_reviews(employer.name, response)

    with log_runtime("Summarize"):
        review_summary = summarize(target, reviews, langchain_config)

    # TODO: Pull out allReviewsCount from glassdoor_results
    return GlassdoorResult(
        target, reviews_url, response, reviews, jobs, review_summary.content
    )


def summarize_sampling(result: GlassdoorResult, alpha=0.05) -> str:
    """Summarize the review stats compared to the overall distribution"""
    # deduplicate the reviews and warn if there are duplicates
    indexed_reviews = dict()
    for review in result.reviews:
        indexed_reviews[review.reviewId] = review
    if len(indexed_reviews) != len(result.reviews):
        print(f"Warning: {len(result.reviews) - len(indexed_reviews)} duplicate reviews found, deduplicating")
    reviews = list(indexed_reviews.values())

    sample_scores = np.array([review.ratingOverall for review in reviews])
    population_mean = result.raw_reviews["ratings"]["overallRating"]
    t_statistic, p_value = stats.ttest_1samp(sample_scores, population_mean)

    min_date = min(review.reviewDateTime for review in reviews)
    max_date = max(review.reviewDateTime for review in reviews)

    # dates as ints
    sample_dates = np.array([review.reviewDateTime.timestamp() for review in reviews])

    # spearman correlation of dates and scores
    date_score_correlation, date_score_p_value = stats.pearsonr(sample_dates, sample_scores)

    return f"""
Overall stats
Mean: {population_mean:.1f}
Count: {result.raw_reviews["ratings"]["reviewCount"]}
      
Sample stats
Mean: {sample_scores.mean():.1f}
Count: {len(sample_scores)}
Date range: {min_date.strftime('%Y-%m-%d')} to {max_date.strftime('%Y-%m-%d')}

Sample reliability
T-statistic: {t_statistic:.3f}
P-value: {p_value:.3f}
{"Sample is significantly different" if p_value < alpha else "Sample is not significantly different"}

Date-score correlation, from the sample
Correlation: {date_score_correlation:.3f}
P-value: {date_score_p_value:.3f}
{"Correlation is significant" if date_score_p_value < alpha else "Correlation is not significant"}
"""