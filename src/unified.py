import re
from typing import Mapping, Optional
import jinja2
from datetime import datetime
import subprocess
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.callbacks.manager import trace_as_chain_group

import markdown
from pydantic import BaseModel

from core import (
    Seed,
    log_summary_metrics,
    eval_filename,
    URLShortener,
)

import data_sources.reddit.search

import data_sources.glassdoor as glassdoor
import data_sources.news as news
import data_sources.company_webpage as company_webpage
import data_sources.crunchbase as crunchbase

import data_sources.general_search as general_search
from loguru import logger

import data_sources.customer_experience as customer_experience
from utils.llm_utils import cleanse_markdown
from utils.markdown_utils import nest_markdown, strip_cache_links

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
When making lists in markdown, include an extra newline before the first list item for compatibility with our formatter, such as:

- item 1
- item 2
...

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
        
    return Review(header=header.strip(), body=body.strip())

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

class Lineage(BaseModel):
    run_at: datetime
    git_sha: str

def markdown_to_html(md: str, add_header_levels=0) -> str:
    if add_header_levels:
        md = nest_markdown(md, add_header_levels)

    # strip cache links
    md = strip_cache_links(md)

    return markdown.markdown(md)

class UnifiedResult(BaseModel):
    summary_markdown: str
    target: Seed

    webpage_result: company_webpage.WebpageResult
    general_search_markdown: str
    crunchbase_markdown: Optional[str]
    customer_experience_result: Optional[customer_experience.CustomerExperienceResult]
    glassdoor_result: Optional[glassdoor.GlassdoorResult]
    news_result: Optional[news.NewsSummary]

    lineage: Lineage

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
    
    def to_html_file(self, path: Optional[str] = None) -> str:
        """
        Format the result into an HTML file and return the filename.
        """
        # TODO: Refactor this whole thing to not do the file I/O, so that it's testable, etc
        if self.customer_experience_result:
            urls_to_div_ids = {url: url_to_div_id(url) for url in self.customer_experience_result.url_to_review.keys()}
            div_ids_to_reviews = {url_to_div_id(url): split_review(markdown_review) for url, markdown_review in self.customer_experience_result.url_to_review.items()}
        else:
            urls_to_div_ids = {}
            div_ids_to_reviews = {}

        if not path:
            path = eval_filename(self.target, extension="html")

        with open(path, "w") as f:

            html = templates.get_template("company.html").render(
                summary=markdown_to_html(self.summary_markdown),
                customer_experience_summary=markdown_to_html(self.customer_experience_markdown, 1),
                employee_experience_summary=markdown_to_html(self.glassdoor_markdown, 1),
                general_search_summary=markdown_to_html(self.general_search_markdown, 1),
                div_ids_to_reviews=div_ids_to_reviews,
                urls_to_div_ids=urls_to_div_ids,
                title=self.target.company,
                result=self,
            )
            f.write(html)

        logger.info(f"Written to {f.name}")

        return f.name
    
def override_app_store_urls(target: Seed, app_store_urls: dict):
    if target.primary_product:
        # TODO: Refactor so that they have the same names and we can just iterate over the names
        if target.primary_product.apple_app_store_url:
            app_store_urls["apple_store_url"] = target.primary_product.apple_app_store_url
        if target.primary_product.google_play_url:
            app_store_urls["google_play_url"] = target.primary_product.google_play_url
        if target.primary_product.steam_url:
            app_store_urls["steam_url"] = target.primary_product.steam_url

async def run(
    target: Seed,
    num_reddit_threads=2,
    max_glassdoor_review_pages=1,
    max_glassdoor_job_pages=0,
    max_news_articles=10,
) -> UnifiedResult:
    """
    Search the web for information on the target company and product, then summarize it all.
    """

    with trace_as_chain_group("Summarize Company", inputs={"seed": target}) as tracing_callback:
        langchain_config = {"callbacks": tracing_callback}

        dynamic_contexts = {}

        crunchbase_markdown = await crunchbase.run(target)
        if crunchbase_markdown:
            dynamic_contexts["Crunchbase"] = crunchbase_markdown

        webpage_summary = await company_webpage.run(target.domain, langchain_config=langchain_config)
        news_result = await news.run(target, max_results=max_news_articles, langchain_config=langchain_config)

        general_search_results = general_search.search_web(target)
        search_results = general_search_results + webpage_summary.search_results
        if news_result:
            search_results += news_result.search_results
        general_search_summary = general_search.summarize(
            target, search_results, langchain_config=langchain_config
        ).content

        app_store_urls = customer_experience.extract_app_store_urls(general_search_results)
        override_app_store_urls(target, app_store_urls)
        reddit_urls = [
            result.link
            for result in data_sources.reddit.search.find_submissions(
                target, num_results=num_reddit_threads
            )
        ]
        customer_experience_result = await customer_experience.run(
            target, reddit_urls=reddit_urls, langchain_config=langchain_config, **app_store_urls
        )

        glassdoor_result = await glassdoor.run(
            target,
            max_review_pages=max_glassdoor_review_pages,
            max_job_pages=max_glassdoor_job_pages,
            langchain_config=langchain_config,
        )


        unshortened_context = "\n\n".join(
            [
                webpage_summary.summary_markdown,
                news_result.summary_markdown if news_result else "",
            ]
            + list(dynamic_contexts.values())
        )

        url_shortener = URLShortener()

        llm = ChatOpenAI(model="gpt-4o", temperature=0)

        runnable = prompt | llm
        result = runnable.with_config({"run_name": "Combine All Summaries"}).invoke(
            {
                "company_name": target.company,
                "product_name": target.product,
                "company_domain": target.domain,
                "company_webpage_text": url_shortener.shorten_markdown(
                    webpage_summary.summary_markdown
                ),
                "news_text": url_shortener.shorten_markdown(news_result.summary_markdown) if news_result else "",
                "dynamic_contexts": url_shortener.shorten_markdown(
                    contexts_to_markdown(dynamic_contexts)
                ),
            },
            langchain_config,
        )
        result.content = url_shortener.unshorten_markdown(cleanse_markdown(result.content))

        log_summary_metrics(result.content, unshortened_context, extractive=False)

        return UnifiedResult(
            target=target,
            summary_markdown=result.content,
            webpage_result=webpage_summary,
            general_search_markdown=general_search_summary,
            customer_experience_result=customer_experience_result,
            glassdoor_result=glassdoor_result,
            news_result=news_result,
            crunchbase_markdown=crunchbase_markdown,
            lineage=Lineage(run_at=datetime.now(), git_sha=git_sha()),
        )


