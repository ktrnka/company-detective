from datetime import date
from pydantic import BaseModel

from typing import List, Optional, Tuple

class FundingRound(BaseModel):
    announced_on: date
    raised_usd: Optional[int]
    investors: Optional[int]
    lead_investors: Optional[List[str]]

class Article(BaseModel):
    title: Optional[str]
    author: Optional[str]
    publisher: Optional[str]
    url: Optional[str]
    date: date
    type: str

    @property
    def is_news(self):
        return self.title is not None and self.url is not None

class Organization(BaseModel):
    """Data model for the organization response from Scrapfly Crunchbase API"""
    id: str
    name: str
    logo: str
    description: str
    founded_on: date
    linkedin: str
    facebook: Optional[str]
    twitter: str
    email: str
    website: str
    ipo_status: str
    rank_org_company: int
    semrush_global_rank: int
    semrush_visits_latest_month: int
    semrush_id: str
    categories: List[str]
    legal_name: str
    operating_status: str
    funding_rounds: List[FundingRound]
    timeline: List[Article]
    funding_total_usd: int

    @property
    def news(self):
        return sorted([article for article in self.timeline if article.is_news], key=lambda article: article.date, reverse=True)
    
    @property
    def filtered_funding_rounds(self):
        return sorted([round for round in self.funding_rounds if round.raised_usd], key=lambda round: round.announced_on, reverse=True)
    
    @property
    def url(self):
        return f"https://www.crunchbase.com/organization/{self.id}"


class Employee(BaseModel):
    """Data model for each employee response from Scrapfly Crunchbase API"""
    job_departments: Optional[List[str]]
    job_levels: List[str]
    linkedin: str
    name: str

def parse(response: dict) -> Tuple[Organization, List[Employee]]:
    return Organization(**response["organization"]), [Employee(**emp) for emp in response["employees"]]
