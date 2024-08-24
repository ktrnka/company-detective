from functools import lru_cache
from src.google_search import search, SearchResult
from core import CompanyProduct, log_summary_metrics
import scrapfly_scrapers.indeed
from .models import JobDetails, JobOverview
from markdownify import markdownify as md


from typing import List
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages.ai import AIMessage
from langchain_openai import ChatOpenAI

scrapfly_scrapers.indeed.BASE_CONFIG["cache"] = True


@lru_cache
def find_indeed_jobs(target: CompanyProduct) -> SearchResult:
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
You'll also be provided with a recent job title of a prospective candidate.

Review all job descriptions and summarize key information and insights that may be relevant for this candidate.
Examples of information that would be useful include:
- For highly relevant roles, a summary of what's special or unique about the roles at this company compared to other companies working in the same field
- If there are different seniority levels of relevant roles, a summary of general expectations for each level
- In a software engineering role, a summary of technologies used or skills required separated by type (e.g, machine learning, data engineering, backend engineering, frontend engineering)
- A summary of any unique benefits or perks offered by the company
- A summary of the company's culture and values as reflected in the job descriptions
- A summary of the company's growth and expansion plans as reflected in the job descriptions

Format the output as a markdown document.
When summarizing, reference the source of the information with a markdown link, as in ([Job Title](https://permalink)).

At the end of the document, include a list of the sources that were used to generate the summary as a list of markdown links.
            """,
        ),
        (
            "human",
            """
Company: {company_name}
Recent job title(s) of the candidate: {candidate_title}

Job descriptions: 
{text}
            """,
        ),
    ]
)


def summarize(
    target: CompanyProduct, candidate_title: str, job_details: List[JobDetails]
) -> AIMessage:
    """Summarize a list of job descriptions"""
    unified_markdown = "\n\n".join(job_to_markdown(job) for job in job_details)

    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

    runnable = _prompt | llm
    result = runnable.invoke(
        {
            "text": unified_markdown,
            "company_name": target.company,
            "candidate_title": candidate_title,
        }
    )

    log_summary_metrics(result.content, unified_markdown)

    return result


async def run(target: CompanyProduct, candidate_title: str) -> AIMessage:
    company_result = find_indeed_jobs(target)

    # get the job overviews from the company page
    raw_jobs = await scrapfly_scrapers.indeed.scrape_search(company_result.link)
    job_overviews = [JobOverview(**job) for job in raw_jobs]

    # get the job details from each page
    job_keys = [job.jobkey for job in job_overviews]
    raw_job_details = await scrapfly_scrapers.indeed.scrape_jobs(job_keys)
    job_details = [JobDetails(**job) for job in raw_job_details]

    return summarize(target, candidate_title, job_details)
