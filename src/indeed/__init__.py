from functools import lru_cache
from google_search import search, SearchResult
from core import Seed, log_summary_metrics
import scrapfly_scrapers.indeed
from .models import JobDetails, JobOverview
from markdownify import markdownify as md


from typing import List
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages.ai import AIMessage
from langchain_openai import ChatOpenAI

scrapfly_scrapers.indeed.BASE_CONFIG["cache"] = True


@lru_cache
def find_indeed_jobs(target: Seed) -> SearchResult:
    # URL format https://www.indeed.com/cmp/Pomelo-Care/jobs
    results = list(search(f'site:www.indeed.com/cmp "{target.company}"', num=10))
    results = [
        result
        for result in results
        if "/cmp/" in result.link and "/jobs" in result.link
    ]

    assert results, f"No Indeed jobs found for {target.company}"

    return results[0]


def job_to_markdown(job: JobDetails) -> str:
    return f"""
# [{job.jobTitle}]({job.job_link}) at {job.companyName}

{md(job.description)}
"""


_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
You're an expert in gleaning information from corporate job descriptions, and you'll be provided with several open job descriptions from a single company in markdown format. 

Use the following markdown structure to summarize information from the job descriptions:

# About the Company

# Benefits

# Culture and Values

# Technologies by Role

# Bibliography

- [Job Title 1](https://permalink)
...
            """,
        ),
        (
            "human",
            """
Company: {company_name}

Job descriptions: 
{text}
            """,
        ),
    ]
)


def summarize(
    target: Seed, job_details: List[JobDetails]
) -> AIMessage:
    """Summarize a list of job descriptions"""
    unified_markdown = "\n\n".join(job_to_markdown(job) for job in job_details)

    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

    runnable = _prompt | llm
    result = runnable.invoke(
        {
            "text": unified_markdown,
            "company_name": target.company,
        }
    )

    log_summary_metrics(result.content, unified_markdown)

    return result


async def run(target: Seed) -> AIMessage:
    company_result = find_indeed_jobs(target)

    # get the job overviews from the company page
    raw_jobs = await scrapfly_scrapers.indeed.scrape_search(company_result.link)
    job_overviews = [JobOverview(**job) for job in raw_jobs]

    # get the job details from each page
    job_keys = [job.jobkey for job in job_overviews]
    raw_job_details = await scrapfly_scrapers.indeed.scrape_jobs(job_keys)
    job_details = [JobDetails(**job) for job in raw_job_details]

    return summarize(target, job_details)
