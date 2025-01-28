# Key design differences from other modules:
# - We won't have a full citation for each page, just an overall citation and list of pages
# - The results may be highly biased
# - More open-ended summary

from dataclasses import dataclass
from functools import reduce
from typing import List, Optional
from utils.debug import log_runtime
from utils.google_search import SearchResult, search
from utils.scrape import extract_links, response_to_article, article_to_markdown, simplify_links
from utils.async_scrape import scrape
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from core import log_summary_metrics
from loguru import logger

_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
You'll be given several pages from a company website in markdown format.
Read all the webpages carefully and summarize all the content in markdown format.

Guidelines on content:
More valuable: Company history, services, products, customers, leadership team, culture
Less valuable: Legal policies

Guidelines on formatting:
Use markdown format
Include citations where possible, in the format [(Title)](url)
When making lists in markdown, include an extra newline before the first list item for compatibility with our formatter, such as:

- item 1
- item 2
...
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


async def run(website: str, num_pages=30, langchain_config=None) -> WebpageResult:
    assert website, "Website must be non-empty"

    with log_runtime("search"):
        search_results = list(search(f"site:{website}", num=num_pages))

    with log_runtime("scrape"):
        responses = await scrape([result.link for result in search_results])
        responses = [response for response in responses if response and response.ok and response.text]

        # Fallback option if we're very light on pages
        if len(responses) < num_pages // 3:
            logger.warning(f"Only {len(responses)} pages found, falling back to a broader search")
            link_sets = [extract_links(response.url, response.text) for response in responses]
            links = reduce(lambda x, y: x.union(y), link_sets, set())

            # Filter to links from target.domain
            links = {link for link in links if website in link}

            logger.info(f"Found {len(links)} links to crawl: {links}")
            
            # Remove all the pages we've already crawled or attempted to crawl
            # Also strip trailing slashes from the links
            links = simplify_links(links) - simplify_links(result.link for result in search_results)
            logger.info(f"After removing the visited ones: {links}")

            # TODO: Curate this list of links a little better, like removing privacy policies and such
            queue = sorted(links)[:num_pages - len(responses)]
            additional_responses = await scrape(queue)
            additional_responses = [response for response in additional_responses if response and response.ok and response.text]
            logger.info(f"Found {len(additional_responses)} additional pages")
            responses.extend(additional_responses)


    with log_runtime("parse"):
        articles = [response_to_article(response) for response in responses]
        article_markdowns = [article_to_markdown(article) for article in articles]

        joined_markdowns = "\n\n".join(article_markdowns)

    with log_runtime("summarize"):
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
