# Key design differences from other modules:
# - We won't have a full citation for each page, just an overall citation and list of pages
# - The results may be highly biased
# - More open-ended summary

from dataclasses import dataclass
from typing import List, Optional
from utils.google_search import SearchResult, search
from utils.scrape import request_article, response_to_article, article_to_markdown
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from core import log_summary_metrics

_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
You'll be given several pages from a company website in markdown format.
Read all the webpages carefully and summarize all the content in markdown format.

Include citations where possible, in the format [(Title)](url)

These are guidelines about what information to include:
More valuable: Company history, services, products, customers, leadership team, culture
Less valuable: Legal policies
            """,
        ),
        (
            "human",
            """
Webpages:
{context}

Summary in markdown format:
            """,
        ),
    ]
)


@dataclass
class WebpageResult:
    summary_markdown: str
    page_markdowns: List[str]
    search_results: Optional[List[SearchResult]] = None


def run(website: str, num_pages=30, langchain_config=None) -> WebpageResult:
    assert website, "Website must be non-empty"

    search_results = list(search(f"site:{website}", num=num_pages))

    responses = [request_article(result.link) for result in search_results]
    responses = [response for response in responses if response and response.ok]

    articles = [response_to_article(response) for response in responses]
    article_markdowns = [article_to_markdown(article) for article in articles]

    joined_markdowns = "\n\n".join(article_markdowns)

    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    runnable = _prompt | llm
    result = runnable.with_config({"run_name": "Summarize Company Webpage"}).invoke(
        {
            # NOTE: I tried the URL shortener initially but had an issue with a dangling cache reference
            "context": joined_markdowns,
        },
        langchain_config
    )

    log_summary_metrics(result.content, joined_markdowns, extractive=False)

    return WebpageResult(
        summary_markdown=result.content,
        page_markdowns=article_markdowns,
        search_results=search_results,
    )
