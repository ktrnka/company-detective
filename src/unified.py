import re
from typing import Mapping, Optional
import jinja2
from datetime import datetime
import subprocess
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
import markdown
from pydantic import BaseModel

from core import (
    Seed,
    log_summary_metrics,
    eval_filename,
    nest_markdown,
    URLShortener,
    cleanse_markdown,
)

import reddit.search

import glassdoor
import news
import crunchbase
import company_webpage

import general_search
from loguru import logger

import customer_experience

templates = jinja2.Environment(
    loader=jinja2.FileSystemLoader("templates"),
)


def git_sha():
    return (
        subprocess.check_output(["git", "rev-parse", "--short", "HEAD"])
        .decode()
        .strip()
    )


def generate_lineage_markdown():
    return f"""
# Lineage

- Run at: {datetime.now().isoformat()}
- Git SHA: {git_sha()}
"""


prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
PERSONA
You're an expert in reviewing and analyzing news about companies and products.
When interpreting information, you understand that all authors impart some bias and perspective according to their incentives and access to information.
You seek to understand the authors to better interpret and debias their information by considering their background, affiliations, and potential motivations.

When assessing product quality:
- Companies typically exaggerate the positive aspects of their products and hide the negative aspects. Hence, you treat company statements about product quality with skepticism and seek corroborating evidence from independent sources.
- Reddit tends to be polarized, often oversampling strong opinions, particularly negative ones. Therefore, you interpret feedback on Reddit by looking for patterns across multiple comments and considering the context of each comment to identify more balanced views.

You review a wide range of sources to get a comprehensive view that's less susceptible to individual biases. You also consider the reliability of each source with respect to the type of information it provides. For example:
- Crunchbase is a reliable source for information about fundraising but less so for the current number of employees.
- News sources can be reliable but must be cross-referenced with other reports to ensure accuracy.

When sharing information with others, you're careful to provide specific details and cite sources so that your readers can easily verify all information. You understand that using quotes and citations builds trust with your audience, as it demonstrates transparency and allows them to see the original context of the information. Including dates in citations is crucial because:
- The date is a key factor in determining relevance. For example, very positive but older sentiment about a company may not indicate much about its current state.
- Certain key details about companies and products can change drastically over time, so noting the general timeframe is crucial for accuracy. For instance, a company may have had 300 employees in 2021 but only 20 employees in 2024. Including the date provides essential context for such information.

You keep facts and opinions clearly separated but share both with your audience to provide a well-rounded perspective. Your goal is to offer as detailed and balanced a view as possible, allowing your audience to make well-informed decisions. You focus on specifics, such as numbers and concrete examples, to provide clarity and support your analysis.

TASK
Carefully review all of the following information about a company and its product.
Write a comprehensive report with citations to the original sources for reference.

OUTPUT CONTENT AND FORMAT

Loosely follow this template in your report. Each markdown section has tips on what information is most critical.

# About {company_name}

The About section should provide all the essential information about the company.
An ideal section should at least incorporate the answers to the following questions, if available:
- When was the company founded?
- Approximately how many employees work at the company?
- What products does the company produce? What services does the company offer?
- How does the company make money? Who are their customers in general? Is it B2B, B2C? If B2B, include example customers.
- Approximately how much revenue does the company generate annually?
- Describe the scale of the company if possible, including the number of customers, users, or clients.
- How are the company's products distributed or sold to users?
- How has the company changed over time?
- How do third parties describe the company, compared to how the company describes itself?

# Key personnel

Include the names and roles of any key personnel at the company. If possible, provide a brief summary of their background and experience as well as any sentiments expressed about them in the sources.

# News

This section should include news articles about the company in reverse chronological order, grouped by topic or event as needed.

# Additional reading

This section should organize any additional links that the reader might find useful for further research.


Feel free to create subheadings or additional sections as needed to capture all relevant information about the company and its product.
Format the output as a markdown document, using markdown links for citations.
Citations should follow the format [(Author or Title, Source, Date)](cache://source/number).
            """,
        ),
        (
            "human",
            """
Company: {company_name}
Product: {product_name}

Summary of {company_domain}:
{company_webpage_text}

News sources:
{news_text}

{dynamic_contexts}
            """,
        ),
    ]
)


def contexts_to_markdown(contexts: Mapping[str, str]) -> str:
    return "\n\n".join([f"{key}\n{value}" for key, value in contexts.items()])

class Review(BaseModel):
    header: str
    body: str

def split_review(markdown_review: str) -> Review:
    # Split the markdown review into header and body
    header, body = markdown_review.strip().split("\n", 1)

    # Remove the markdown header
    header = re.sub(r'#.*?\s+', '', header)

    # Remove the link from the header
    header = re.sub(r'\[(.*?)\]\(.*?\)', '\\1', header)
        
    return Review(header=header, body=body)

def test_split_review():
    example_md = """
    # 5 stars [(Pancho, Google Play Store, 2022-12-21)](https://google_play/bfc47476-7378-4727-b0b1-66d76e817be6)
    I was waiting 2 hrs at the urgent care ..."""

    review = split_review(example_md)

    assert review.header.startswith("5 stars")
    assert review.body.startswith("I was waiting 2 hrs")
    assert "http" not in review.header

def url_to_div_id(url: str) -> str:
    """Helper to convert a fake-url to a page-internal div ID for modals"""
    _, url = url.split("://")
    return re.sub(r'\W', '_', url)

class UnifedResult(BaseModel):
    summary_markdown: str
    target: Seed

    webpage_result: company_webpage.WebpageResult
    general_search_markdown: str
    crunchbase_markdown: Optional[str]
    customer_experience_result: Optional[customer_experience.CustomerExperienceResult]
    glassdoor_result: Optional[glassdoor.GlassdoorResult]
    news_result: news.NewsSummary

    @property
    def customer_experience_markdown(self) -> str:
        if self.customer_experience_result:
            return self.customer_experience_result.output_text
        else:
            return "No customer experience information found."
        
    @property
    def glassdoor_markdown(self) -> str:
        if self.glassdoor_result:
            return self.glassdoor_result.summary_markdown
        else:
            return "No Glassdoor information found."

    def to_markdown_file(self) -> str:
        with open(eval_filename(self.target, extension="md"), "w") as f:
            f.write(f"""
{self.summary_markdown}

# Employee sentiment

{nest_markdown(self.glassdoor_markdown, 1)}

# Customer experience
{nest_markdown(self.customer_experience_markdown, 1)}

{generate_lineage_markdown()}

----

# INTERMEDIATE RESULTS BELOW
Note: The report above is an aggregation of all the information below. I like to include the intermediate outputs below for debugging and verification. For instance, if the final output has a very brief section on employee sentiment, I can refer to the Glassdoor and Reddit sections below to see if it's a problem in the overall summarization or if the intermediate results were lacking.

----

# Company webpage
{nest_markdown(self.webpage_result.summary_markdown, 1)}

----

# News
{nest_markdown(self.news_result.summary_markdown, 1)}

----

# Crunchbase

{nest_markdown(self.crunchbase_markdown or "No Crunchbase info found", 1)}

----

# Additional search results
{nest_markdown(self.general_search_markdown, 1)}

"""
        )

        logger.info(f"Written to {f.name}")

        return f.name
    
    def to_html_file(self) -> str:
        urls_to_div_ids = {url: url_to_div_id(url) for url in self.customer_experience_result.url_to_review.keys()}
        div_ids_to_reviews = {url_to_div_id(url): split_review(markdown_review) for url, markdown_review in self.customer_experience_result.url_to_review.items()}


        with open(eval_filename(self.target, extension="html"), "w") as f:

            html = templates.get_template("basic_report.html").render(
                summary=markdown.markdown(self.summary_markdown),
                customer_experience_summary=markdown.markdown(nest_markdown(self.customer_experience_markdown, 1)),
                employee_experience_summary=markdown.markdown(nest_markdown(self.glassdoor_markdown, 1)),
                div_ids_to_reviews=div_ids_to_reviews,
                urls_to_div_ids=urls_to_div_ids,
            )
            f.write(html)

        logger.info(f"Written to {f.name}")

        return f.name
    


async def run(
    target: Seed,
    num_reddit_threads=2,
    max_glassdoor_review_pages=1,
    max_glassdoor_job_pages=0,
    max_news_articles=10,
    glassdoor_url=None,
) -> UnifedResult:
    """
    Search the web for information on the target company and product, then summarize it all.
    """

    dynamic_contexts = {}

    webpage_summary = company_webpage.run(target.domain)

    general_search_results = general_search.search_web(target)
    general_search_summary = general_search.summarize(
        target, general_search_results
    ).content

    crunchbase_markdown = await crunchbase.run(target)
    if crunchbase_markdown:
        dynamic_contexts["Crunchbase"] = crunchbase_markdown
    else:
        logger.warning("No Crunchbase info found")

    app_store_urls = customer_experience.extract_app_store_urls(general_search_results)
    reddit_urls = [
        result.link
        for result in reddit.search.find_submissions(
            target, num_results=num_reddit_threads
        )
    ]
    customer_experience_result = customer_experience.run(
        target, reddit_urls=reddit_urls, **app_store_urls
    )

    glassdoor_result = await glassdoor.run(
        target,
        max_review_pages=max_glassdoor_review_pages,
        max_job_pages=max_glassdoor_job_pages,
        url_override=glassdoor_url,
    )

    news_result = news.run(target, max_results=max_news_articles)

    unshortened_context = "\n\n".join(
        [
            webpage_summary.summary_markdown,
            news_result.summary_markdown,
            # general_search_summary,
        ]
        + list(dynamic_contexts.values())
    )

    url_shortener = URLShortener()

    llm = ChatOpenAI(model="gpt-4o", temperature=0)

    runnable = prompt | llm
    result = runnable.invoke(
        {
            "company_name": target.company,
            "product_name": target.product,
            "company_domain": target.domain,
            "company_webpage_text": url_shortener.shorten_markdown(
                webpage_summary.summary_markdown
            ),
            "news_text": url_shortener.shorten_markdown(news_result.summary_markdown),
            # "search_text": url_shortener.shorten_markdown(general_search_summary),
            "dynamic_contexts": url_shortener.shorten_markdown(
                contexts_to_markdown(dynamic_contexts)
            ),
        }
    )
    result.content = url_shortener.unshorten_markdown(cleanse_markdown(result.content))

    log_summary_metrics(result.content, unshortened_context, extractive=False)

    return UnifedResult(
        target=target,
        summary_markdown=result.content,
        webpage_result=webpage_summary,
        general_search_markdown=general_search_summary,
        crunchbase_markdown=crunchbase_markdown,
        customer_experience_result=customer_experience_result,
        glassdoor_result=glassdoor_result,
        news_result=news_result,
    )


