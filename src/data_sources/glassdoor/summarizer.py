from typing import List
import jinja2
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages.ai import AIMessage


from core import Seed, log_summary_metrics
from .models import GlassdoorReview

templates = jinja2.Environment(
    loader=jinja2.FileSystemLoader("templates"),
)

_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
Please extract a comprehensive list of quotes from Glassdoor reviews for the company {company}.
Ensure that all opinions and sentiments are accurately represented.

Organize the quotes into categories as appropriate.
Take extra care to find quotes of 1) explanations why employees like or dislike working for the company, 2) key events or changes in the company, and 3) any verifyable facts about working at the company.
Format the response as Markdown.

Format quotations as: "quote" [(Job title, Glassdoor, Date)](url)
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


def summarize(target: Seed, reviews: List[GlassdoorReview], langchain_config=None) -> AIMessage:
    """Summarize a list of Glassdoor reviews"""
    combined_markdown = "\n\n".join(
        templates.get_template("glassdoor_review.md").render(review=review)
        for review in reviews
    )

    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    runnable = _prompt | llm
    result = runnable.with_config({"run_name": "Summarize Glassdoor"}).invoke(
        {
            "text": combined_markdown,
            "company": target.company,
        },
        langchain_config,
    )

    log_summary_metrics(result.content, combined_markdown)

    return result
