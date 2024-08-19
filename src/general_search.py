from typing import List
from core import CompanyProduct, cleanse_markdown
from search import search, SearchResult
from typing import List
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages.ai import AIMessage
from langchain_openai import ChatOpenAI

from core import CompanyProduct, URLShortener
from dotenv import load_dotenv
from loguru import logger

from typing import List
from search import SearchResult

load_dotenv()


def search_web(target: CompanyProduct) -> List[SearchResult]:
    # Search for the company
    search_results = list(search(f'"{target.company}"', num=100))

    # If the product is not the same as the company, search for the product too
    if target.product != target.company:
        search_results += list(
            search(f'"{target.company}" "{target.product}"', num=100)
        )
    return search_results


_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
You're an expert at organizing search results.
Given search results for a company or product, organize them into the following headers:

# Official social media
# Job boards
# App stores
# Product reviews
# News articles (most recent first, grouped by event)
# Key employees (with subheaders by employee)
# Other pages on the company website
# Business intelligence websites
# Other

Include the publication date after the link, if available.

Unless otherwise specified, order the results in each section from most to least relevant.
Format the output as a markdown document, preserving any links in the source.
Organize ALL search results into these headers; do not omit any results.
            """,
        ),
        (
            "human",
            """
Company: {company_name}
Product: {product_name}

Search results: 
{text}
            """,
        ),
    ]
)


def result_to_markdown(search_result: SearchResult) -> str:
    return f"[{search_result.title}]({search_result.link})\n{search_result.snippet}"


def results_to_markdown(search_results: List[SearchResult]) -> str:
    return "\n\n".join(result_to_markdown(result) for result in search_results)


def summarize(
    target: CompanyProduct,
    search_results: List[SearchResult],
) -> AIMessage:
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    unified_markdown = results_to_markdown(search_results)

    url_shortener = URLShortener()

    runnable = _prompt | llm
    result = runnable.invoke(
        {
            "text": url_shortener.shorten_markdown(unified_markdown),
            "company_name": target.company,
            "product_name": target.product,
        }
    )
    cleanse_markdown(result)

    result.content = url_shortener.unshorten_markdown(result.content)

    logger.info(
        f"{len(unified_markdown):,} -> {len(result.content):,} chars ({len(result.content) / len(unified_markdown):.0%})"
    )

    return result
