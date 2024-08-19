from typing import List
import jinja2
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages.ai import AIMessage

from loguru import logger

from core import CompanyProduct, extract_suspicious_urls, extractive_fraction, extractive_fraction_urls, num_cache_mentions
from .models import GlassdoorReview

templates = jinja2.Environment(
    loader=jinja2.FileSystemLoader("templates"),
)

review_summary_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
Please extract a comprehensive list of quotes from Glassdoor reviews for the company {company}.
Ensure that all opinions and sentiments are accurately represented.

Organize the quotes into categories as appropriate.
Take extra care to find quotes of 1) explanations why employees like or dislike working for the company, 2) key events or changes in the company, and 3) any verifyable facts about working at the company.
Format the response as Markdown.

Format quotations as: "quote" [Job title, Glassdoor, date](url)
            """,
        ),
        (
            "human",
            """
COMPANY OF INTEREST: {company}

EMPLOYEE REVIEWS: 
{text}
            """,
        ),
    ]
)


def summarize(target: CompanyProduct, reviews: List[GlassdoorReview]) -> AIMessage:
    """Summarize a list of Glassdoor reviews"""
    content_string = "\n\n".join(
        templates.get_template("glassdoor_review.md").render(review=review)
        for review in reviews
    )

    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    runnable = review_summary_prompt | llm
    result = runnable.invoke(
        {
            "text": content_string,
            "company": target.company,
        }
    )

    summary_ratio = len(result.content) / len(content_string)
    logger.info(
        "{:,} -> {:,} chars ({:.0%})",
        len(content_string),
        len(result.content),
        summary_ratio,
    )
    
    # Smoke tests
    logger.info("Extractive fraction: {:.0%}", extractive_fraction(result.content, content_string))
    logger.info("Percent of URLs in sources: {:.0%}", extractive_fraction_urls(result.content, content_string))
    logger.info("Suspicious URLs: {}", extract_suspicious_urls(result.content, content_string))
    logger.info("Cache mentions: {} (should be zero)", num_cache_mentions(result.content))

    

    return result
