from dataclasses import dataclass
from datetime import datetime, timedelta
from itertools import chain
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
class Icon:
    name: str
    css_class: str
    extra_text: Optional[str] = None
    tooltip: Optional[str] = None


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

    def html_stats(self) -> str:
        """WORK IN PROGRESS: Generate the high-level stats display for the HTML. It's a simplified version of summarize_sampling"""
        # TODO: Refactor this whole function. Some of this needs to be moved into the template at least
        reviews = GlassdoorReview.deduplicate(self.reviews)

        population_mean = self.raw_reviews["ratings"]["overallRating"]
        if population_mean >= 4.68:
            population_icon = Icon("sentiment_very_satisfied", "green-text")
        elif population_mean >= 4.0:
            population_icon = Icon("sentiment_satisfied", "grey-text")
        elif population_mean >= 3.68:
            population_icon = Icon("sentiment_neutral", "grey-text")
        elif population_mean >= 3.5:
            population_icon = Icon("sentiment_dissatisfied", "grey-text")
        else:
            population_icon = Icon("sentiment_very_dissatisfied", "red-text")

        population_icon.tooltip = f"The icon and color represent the approximate quartile of the overall rating compared to companies we reviewed. Note that ratings tend to vary by industry and role, so it's better to gauge the company's rating relative to its peers on Glassdoor."

        sample_scores = np.array([review.ratingOverall for review in reviews])
        if len(sample_scores) < 2:
            # Can't do a test with only one sample. Treat it like an unreliable sample
            t_statistic = np.nan
            p_value = 0
        else:
            t_statistic, p_value = stats.ttest_1samp(sample_scores, population_mean)

        sample_icon = (
            Icon("check", "green-text")
            if p_value >= 0.05
            else Icon("error", "orange-text")
        )
        sample_icon.tooltip = f"t-statistic={t_statistic:.3f}, p={p_value:.3f} in testing difference between sample and population means"

        min_date = min(review.reviewDateTime for review in reviews).strftime("%Y-%m-%d")
        max_date = max(review.reviewDateTime for review in reviews).strftime("%Y-%m-%d")

        # dates as ints
        sample_dates = np.array(
            [review.reviewDateTime.timestamp() for review in reviews]
        )

        # Pearson isn't applicable if one of the variables is constant
        if len(sample_dates) < 2 or np.std(sample_dates) == 0 or np.std(sample_scores) == 0:
            date_score_correlation = 0
            date_score_p_value = 1
        else:
            date_score_correlation, date_score_p_value = stats.pearsonr(
                sample_dates, sample_scores
            )
        trending_icon = Icon("trending_flat", "grey-text", "steady")
        if date_score_p_value < 0.05:
            if date_score_correlation > 0:
                trending_icon = Icon("trending_up", "green-text", "up")
            else:
                trending_icon = Icon("trending_down", "red-text", "down")
        trending_icon.tooltip = f"Pearson r={date_score_correlation:.3f}, p={date_score_p_value:.3f} in testing correlation between review datetime and score"

        return f"""
        <ul>
            <li title="{population_icon.tooltip}"><span style="display: flex; align-items: center;"><i class="material-icons {population_icon.css_class}">{population_icon.name}</i> Overall rating: {population_mean:.1f} in {self.num_raw_reviews} reviews</span></li>
            <li title="{sample_icon.tooltip}"><span style="display: flex; align-items: center;"><i class="material-icons {sample_icon.css_class}">{sample_icon.name}</i> Sample rating: {sample_scores.mean():.1f} in {self.num_parsed_reviews} reviews</span></li>
            <li title="{trending_icon.tooltip}"><span style="display: flex; align-items: center;"><i class="material-icons {trending_icon.css_class}">{trending_icon.name}</i> Trending {trending_icon.extra_text} from {min_date} to {max_date}</span></li>
        </ul>
        """


def find_glassdoor_employer(target: Seed) -> Optional[EmployerKey]:
    query = f'site:www.glassdoor.com {target.company} "{target.domain}"'
    urls = list(search(query, num=10))
    return UrlBuilder.find_employer_key([result.link for result in urls])

FULL_TTL = timedelta(days=60)
UPDATE_TTL = FULL_TTL / 2

def merge_reviews(old_reviews: List[dict], new_reviews: List[dict]) -> List[dict]:
    """Merge two lists of reviews, deduplicating by reviewId"""
    deduped = dict()
    for review in chain(old_reviews, new_reviews):
        deduped[review["reviewId"]] = review

    logger.info("Merged {} old reviews with {} new reviews into {} total", len(old_reviews), len(new_reviews), len(deduped))

    return list(deduped.values())

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

        response, expire_time_seconds = cache.get(reviews_url, expire_time=True)
        logger.info("Glassdoor cache expire time: {}", datetime.fromtimestamp(expire_time_seconds))

        if not response:
            response = await scrape_reviews(reviews_url, max_pages=max_review_pages)
            if not response:
                logger.warning("No reviews found for {}, exiting early", target.company)
                return None
            cache.set(reviews_url, response, expire=FULL_TTL.total_seconds())

            logger.debug("Glassdoor response: {}", response)
        elif datetime.fromtimestamp(expire_time_seconds) - datetime.now() < UPDATE_TTL:
            updated_data = await scrape_reviews(reviews_url, max_pages=1)

            # NOTE: I don't like how we're "doing surgery" on the response like this, though it's how Scrapfly works under the hood
            updated_data["reviews"] = merge_reviews(response["reviews"], updated_data["reviews"])
            response = updated_data

            cache.set(reviews_url, response, expire=FULL_TTL.total_seconds())

            logger.info("Glassdoor update-merge")
        else:
            logger.info("Using cached reviews")

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
        print(
            f"Warning: {len(result.reviews) - len(indexed_reviews)} duplicate reviews found, deduplicating"
        )
    reviews = list(indexed_reviews.values())

    sample_scores = np.array([review.ratingOverall for review in reviews])
    population_mean = result.raw_reviews["ratings"]["overallRating"]

    t_statistic, p_value = stats.ttest_1samp(sample_scores, population_mean)

    min_date = min(review.reviewDateTime for review in reviews)
    max_date = max(review.reviewDateTime for review in reviews)

    # dates as ints
    sample_dates = np.array([review.reviewDateTime.timestamp() for review in reviews])

    # spearman correlation of dates and scores
    date_score_correlation, date_score_p_value = stats.pearsonr(
        sample_dates, sample_scores
    )

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
