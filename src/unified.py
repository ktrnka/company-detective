from typing import Mapping
import jinja2
from datetime import datetime
import subprocess
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from scrapfly import ScrapflyAspError

from core import (
    Seed,
    log_summary_metrics,
    eval_filename,
    nest_markdown,
    URLShortener,
    cleanse_markdown,
)

import reddit.search
from glassdoor import run as process_glassdoor
from news import run as process_news
from crunchbase import run as process_crunchbase
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


async def run(
    target: Seed,
    num_reddit_threads=2,
    max_glassdoor_review_pages=1,
    max_glassdoor_job_pages=0,
    max_news_articles=10,
    glassdoor_url=None,
):
    """
    Search the web for information on the target company and product, then summarize it all.
    """

    dynamic_contexts = {}

    webpage_summary = company_webpage.run(target.domain)

    general_search_results = general_search.search_web(target)
    general_search_summary = general_search.summarize(
        target, general_search_results
    ).content

    crunchbase_markdown = await process_crunchbase(target)
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

    glassdoor_result = await process_glassdoor(
        target,
        max_review_pages=max_glassdoor_review_pages,
        max_job_pages=max_glassdoor_job_pages,
        url_override=glassdoor_url,
    )

    news_result = process_news(target, max_results=max_news_articles)

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

    if customer_experience_result:
        customer_experience_markdown = customer_experience_result["output_text"]
    else:
        customer_experience_markdown = "No customer experience information found."

    if glassdoor_result:
        glassdoor_markdown = glassdoor_result.summary_markdown
    else:
        glassdoor_markdown = "No Glassdoor information found."

    with open(eval_filename(target, extension="md"), "w") as f:
        f.write(
            f"""
{result.content}

# Employee sentiment

{nest_markdown(glassdoor_markdown, 1)}

# Customer experience
{nest_markdown(customer_experience_markdown, 1)}

{generate_lineage_markdown()}

----

# INTERMEDIATE RESULTS BELOW
Note: The report above is an aggregation of all the information below. I like to include the intermediate outputs below for debugging and verification. For instance, if the final output has a very brief section on employee sentiment, I can refer to the Glassdoor and Reddit sections below to see if it's a problem in the overall summarization or if the intermediate results were lacking.

----

# Company webpage
{nest_markdown(webpage_summary.summary_markdown, 1)}

----

# News
{nest_markdown(news_result.summary_markdown, 1)}

----

# Additional search results
{nest_markdown(general_search_summary, 1)}

"""
        )

        for source, content in dynamic_contexts.items():
            f.write(f"# {source}\n{nest_markdown(content, 1)}\n")

        logger.info(f"Written to {f.name}")

        return f.name
