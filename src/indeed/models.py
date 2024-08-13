from pydantic import BaseModel, model_validator
from typing import List, Dict, Optional
import urllib.parse


class Salary(BaseModel):
    currency: str
    salaryTextFormatted: bool
    source: Optional[str]
    text: Optional[str]

    @model_validator(mode="before")
    def _allow_missing_optional(cls, data):
        if "source" not in data:
            data["source"] = None
        if "text" not in data:
            data["text"] = None
        return data


class Attribute(BaseModel):
    label: str
    suid: str


class Attributes(BaseModel):
    attributes: List[Attribute]
    label: str


class JobOverview(BaseModel):
    """The overview of a job, found on the company page"""

    createDate: int
    displayTitle: str
    expired: bool
    formattedLocation: str
    formattedRelativeTime: str
    jobLocationCity: str
    jobkey: str
    pubDate: int
    remoteLocation: bool
    title: str
    salarySnippet: Salary
    truncatedCompany: str
    taxonomyAttributes: List[Attributes]


class JobDetails(BaseModel):
    companyName: str
    companyOverviewLink: str
    companyReviewLink: str
    description: str  # html formatted
    formattedLocation: str
    jobNormTitle: Optional[str]
    jobTitle: str
    jobType: str
    jobTypes: Optional[List[str]]
    location: Optional[str]
    remoteLocation: bool
    remoteWorkModel: Dict
    salaryCurrency: Optional[str]
    salaryMax: Optional[int]
    salaryMin: Optional[int]
    salaryType: Optional[str]
    subtitle: str

    @property
    def job_key(self):
        """Extract the job key from existing data; it's not provided in a separate field"""
        # Extract the GET param "fromjk" from the companyOverviewLink
        query = urllib.parse.urlparse(self.companyOverviewLink).query
        return urllib.parse.parse_qs(query)["fromjk"][0]

    @property
    def job_link(self):
        """Permalink to the job listing"""
        return f"https://www.indeed.com/viewjob?jk={self.job_key}"
