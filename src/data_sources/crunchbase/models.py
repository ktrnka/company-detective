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
    logo: Optional[str] = None
    description: Optional[str] = ""
    founded_on: Optional[date] = None
    linkedin: Optional[str] = None
    facebook: Optional[str] = None
    twitter: Optional[str] = None
    email: Optional[str] = None
    website: str
    ipo_status: str
    rank_org_company: int
    semrush_global_rank: Optional[int] = None
    semrush_visits_latest_month: Optional[int] = None
    semrush_id: Optional[str] = None
    categories: Optional[List[str]] = []
    legal_name: Optional[str] = None
    operating_status: str
    funding_rounds: List[FundingRound]
    timeline: List[Article]
    funding_total_usd: Optional[int] = None

    @property
    def news(self):
        return sorted([article for article in self.timeline if article.is_news], key=lambda article: article.date, reverse=True)
    
    @property
    def filtered_funding_rounds(self):
        return sorted([round for round in self.funding_rounds if round.raised_usd], key=lambda round: round.announced_on, reverse=True)
    
    @property
    def url(self):
        return f"https://www.crunchbase.com/organization/{self.id}"

