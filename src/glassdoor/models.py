from datetime import datetime
import re
from typing import Optional, NamedTuple
from pydantic import BaseModel

from scrapfly_scrapers.glassdoor import Url


class EmployerKey(NamedTuple):
    name: str
    id: str


class UrlBuilder(Url):
    """Utility functions for Glassdoor URLs, beyond the Scrapfly utility functions"""

    @staticmethod
    def review(employer: str, review_id: int) -> str:
        employer = employer.replace(" ", "-")
        return f"https://www.glassdoor.com/Reviews/Employee-Review-{employer}-RVW{review_id}.htm"

    @staticmethod
    def parse_review_url(url: str) -> Optional[EmployerKey]:
        """
        Parse Glassdoor review page URL to get employer name and ID
        e.g. https://www.glassdoor.com/Reviews/eBay-Reviews-E7853.htm
        returns ("eBay", "7853")
        """
        groups = re.search(r"/Reviews/(.*)-Reviews-E([0-9A-F]+).htm", url).groups()

        if groups:
            return EmployerKey(*groups)
        return None


class JobTitle(BaseModel):
    """Glassdoor job title with ID"""

    id: int
    text: str


class GlassdoorReview(BaseModel):
    """An employee review of a company on Glassdoor"""

    advice: Optional[str]
    cons: Optional[str]
    lengthOfEmployment: int
    pros: Optional[str]
    ratingOverall: int
    reviewId: int
    summary: str
    jobTitle: Optional[JobTitle]
    reviewDateTime: Optional[datetime]

    # The Glassdoor URL part for the employer, used to build the full URL
    employer_url_part: str

    @property
    def formatted_job_title(self) -> str:
        return self.jobTitle.text if self.jobTitle else "Anonymous"

    @property
    def url(self) -> str:
        return UrlBuilder.review(self.employer_url_part, self.reviewId)

    @classmethod
    def parse_reviews(cls, employer_url_part: str, raw_results: dict):
        """Parse Glassdoor reviews from the raw API response"""
        # NOTE: I don't feel good about the design of employer_url_part because I'd like to be able to use the raw pydantic parsing
        parsed_reviews = [
            cls(employer_url_part=employer_url_part, **review)
            for review in raw_results["reviews"]
        ]
        parsed_reviews = sorted(
            parsed_reviews, key=lambda x: x.reviewDateTime, reverse=False
        )

        return parsed_reviews


class EmployerRatings(BaseModel):
    """Aggregate ratings for a company on Glassdoor"""

    __typename: str
    businessOutlookRating: float
    careerOpportunitiesRating: float
    ceoRating: float
    compensationAndBenefitsRating: float
    cultureAndValuesRating: float
    diversityAndInclusionRating: float
    overallRating: float
    # ratedCeo: RatedCeo
    recommendToFriendRating: float
    reviewCount: int
    seniorManagementRating: float
    workLifeBalanceRating: float


class GlassdoorJob(BaseModel):
    """Basic job listing info from the company page on Glassdoor"""

    ageInDays: int
    goc: str
    jobTitleText: str
    locationName: str
    payCurrency: str
    payPercentile10: Optional[int]
    payPercentile50: Optional[int]
    payPercentile90: Optional[int]
    payPeriod: Optional[str]
    salarySource: Optional[str]
    seoJobLink: str
