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
        match = re.search(r"/Reviews/(.*)-Reviews-E([0-9A-F]+).htm", url)

        if match:
            return EmployerKey(*match.groups())
        return None

    @staticmethod
    def parse_overview_url(url: str) -> Optional[EmployerKey]:
        match = re.search(r"/Overview/Working-at-(.+)-EI_IE([0-9]+).\d+,\d+.htm", url)
        if match:
            return EmployerKey(*match.groups())
        return None

    @staticmethod
    def find_employer_key(urls: list[str]) -> Optional[EmployerKey]:
        for url in urls:
            employer_key = UrlBuilder.parse_review_url(url)
            if employer_key:
                return employer_key

            employer_key = UrlBuilder.parse_overview_url(url)
            if employer_key:
                return employer_key
        return None


def test_parse_review_url():
    # When it should work
    assert UrlBuilder.parse_review_url(
        "https://www.glassdoor.com/Reviews/98point6-Reviews-E1181484.htm"
    ) == EmployerKey("98point6", "1181484")

    # When it should return None
    assert UrlBuilder.parse_review_url("https://www.glassdoor.com/Reviews/") == None


def test_parse_overview_url():
    # When it should work
    assert UrlBuilder.parse_overview_url(
        "https://www.glassdoor.com/Overview/Working-at-98point6-EI_IE1181484.11,19.htm"
    ) == EmployerKey("98point6", "1181484")

    # Make sure we handled the part after the ID correctly:
    assert UrlBuilder.parse_overview_url(
        "https://www.glassdoor.com/Overview/Working-at-Kevala-Care-EI_IE5145912.11,22.htm"
    ) == EmployerKey("Kevala-Care", "5145912")

    # When it should return None
    assert UrlBuilder.parse_overview_url("https://www.glassdoor.com/Overview/") == None


def test_find_employer_key():
    # the example that used to fail:
    akili_results = [
        "https://www.glassdoor.com/Overview/Working-at-Akili-Interactive-Labs-EI_IE1796040.11,33.htm",
        "https://www.glassdoor.com/Photos/Akili-Interactive-Labs-Office-Photos-IMG2039679.htm",
        "https://www.glassdoor.com/Salaries/game-designer-intern-salary-SRCH_KO0,20.htm",
        "https://www.glassdoor.com/Salaries/vice-president-of-market-access-salary-SRCH_KO0,31.htm",
        "https://www.glassdoor.com/Salaries/knowledge-manager-salary-SRCH_KO0,17.htm",
        "https://www.glassdoor.com/Salaries/quality-control-assistant-salary-SRCH_KO0,25.htm",
    ]

    assert UrlBuilder.find_employer_key(akili_results) == EmployerKey(
        "Akili-Interactive-Labs", "1796040"
    )

    # another example the used to fail:
    pomelo_results = [
        "https://www.glassdoor.com/Interview/Pomelo-Care-Interview-Questions-E9429297.htm",
        "https://www.glassdoor.com/Salary/Pomelo-Care-Salaries-E9429297.htm",
        "https://www.glassdoor.com/Overview/Working-at-Pomelo-Care-EI_IE9429297.11,22.htm",
        "https://www.glassdoor.com/Reviews/Employee-Review-Pomelo-Care-RVW87236225.htm",
        "https://www.glassdoor.com/Jobs/Pomelo-Care-Jobs-E9429297.htm",
        "https://www.glassdoor.com/Salary/Pomelo-Care-Outreach-and-Engagement-Specialist-Salaries-E9429297_D_KO12,46.htm",
        "https://www.glassdoor.com/Reviews/Pomelo-Care-New-York-Reviews-EI_IE9429297.0,11_IL.12,20_IC1132348.htm",
        "https://www.glassdoor.com/job-listing/bilingual-outreach-engagement-specialist-pomelo-care-JV_KO0,40_KE41,52.htm?jl=1009079567446",
        "https://www.glassdoor.com/job-listing/market-operations-lead-pomelo-care-JV_IC1132348_KO0,22_KE23,34.htm?jl=1008902770882",
        "https://www.glassdoor.com/Benefits/Pomelo-Care-US-Benefits-EI_IE9429297.0,11_IL.12,14_IN1.htm",
    ]

    assert UrlBuilder.find_employer_key(pomelo_results) == EmployerKey(
        "Pomelo-Care", "9429297"
    )

    # test one that won't find anything
    worsened_akili_results = [
        "https://www.glassdoor.com/Photos/Akili-Interactive-Labs-Office-Photos-IMG2039679.htm",
        "https://www.glassdoor.com/Salaries/game-designer-intern-salary-SRCH_KO0,20.htm",
        "https://www.glassdoor.com/Salaries/vice-president-of-market-access-salary-SRCH_KO0,31.htm",
        "https://www.glassdoor.com/Salaries/knowledge-manager-salary-SRCH_KO0,17.htm",
        "https://www.glassdoor.com/Salaries/quality-control-assistant-salary-SRCH_KO0,25.htm",
    ]

    assert UrlBuilder.find_employer_key(worsened_akili_results) == None


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
