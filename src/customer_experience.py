"""
This module produces a unified customer experience summary from multiple different data sources:
- Reddit
- Apple App Store
- Google Play Store
- Steam
"""

from dataclasses import dataclass
from typing import Dict, List, Optional

from langchain_core.documents import Document
from langchain.chains.summarize import load_summarize_chain
from langchain import PromptTemplate
from langchain_openai import ChatOpenAI
from loguru import logger
from pydantic import BaseModel

from core import Seed, URLShortener, extract_urls, log_summary_metrics
import reddit.fetch
from google_search import SearchResult
import app_stores.steam as steam
import app_stores.google_play as google_play
import app_stores.apple as apple_app_store
from llm_utils import pack_documents

map_prompt = """
Please read the following customer comments and extract all opinions and facts relating to the user experience of the PRODUCT {product} by the COMPANY {company} from the perspective of current users.
Only include information about {product}. 
If the text does not contain any relevant information, return an empty string.

Format the results as a Markdown list of quotes, each with a permalink to the source of the quote like so:
- "quote" [(Author, Source, Date)](cache://source/NUM)

If the author is not available, use "Anonymous".

----

Each quote should be a brief statement that captures the essence of the sentiment or information.
Be sure to extract a comprehensive sample of both positive and negative opinions, as well as any factual statements about the product.

REVIEWS: 
{text}

MARKDOWN LIST OF QUOTES ABOUT THE COMPANY {company} AND PRODUCT {product} (markdown only, don't wrap in backticks):
"""
map_prompt_template = PromptTemplate(
    template=map_prompt, input_variables=["text", "company", "product"]
)

combine_prompt = """
Please organize all of the quotes below into topics about the COMPANY {company} and PRODUCT {product}.
Organize into headings based on the sentiment and/or type of information in the quote.

EXTRACTS FROM REVIEWS: 
{text}

ORGANIZED QUOTES IN MARKDOWN FORMAT (markdown only, don't wrap in backticks):
"""
combine_prompt_template = PromptTemplate(
    template=combine_prompt, input_variables=["text", "company", "product"]
)

class CustomerExperienceResult(BaseModel):
    output_text: str
    intermediate_steps: List[str]
    url_to_review: Dict[str, Optional[str]]


def run(
    target: Seed,
    steam_url: Optional[str] = None,
    google_play_url: Optional[str] = None,
    apple_store_url: Optional[str] = None,
    reddit_urls: Optional[List[str]] = None,
) -> Optional[CustomerExperienceResult]:
    review_markdowns = []

    if steam_url:
        steam_id = steam.extract_steam_id(steam_url)
        steam_reviews = steam.get_reviews(steam_id, num_reviews=500)
        review_markdowns.extend(
            steam.review_to_markdown(review) for review in steam_reviews
        )

    if google_play_url:
        google_play_id = google_play.extract_google_play_app_id(google_play_url)
        google_play_reviews = google_play.scrape_reviews(google_play_id)
        review_markdowns.extend(
            google_play.review_to_markdown(review) for review in google_play_reviews
        )

    if apple_store_url:
        apple_app_store_id = apple_app_store.extract_apple_app_store_id(apple_store_url)
        apple_reviews = apple_app_store.scrape(apple_app_store_id)
        review_markdowns.extend(
            apple_app_store.review_to_markdown(review) for review in apple_reviews
        )

    # Index all non-Reddit reviews because their URLs are fake
    url_to_review = {}
    for review in review_markdowns:
        links = extract_urls(review)
        for link in links:
            url_to_review[link] = review

    if reddit_urls:
        reddit_client = reddit.fetch.init()
        reddit_threads = [reddit_client.submission(url=url) for url in reddit_urls]

        # only threads with enough comments
        reddit_threads = [
            submission for submission in reddit_threads if submission.num_comments >= 2
        ]

        review_markdowns.extend(
            reddit.fetch.submission_to_markdown(thread) for thread in reddit_threads
        )

    logger.info("Total reviews: {}", len(review_markdowns))
    if not review_markdowns:
        return None

    # Pack the documents then truncate any very-long ones
    packed_reviews = pack_documents(review_markdowns, max_chars=70000)
    packed_reviews = [doc[:100000] for doc in packed_reviews]

    logger.info("Packed reviews: {}", len(packed_reviews))

    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

    shortener = URLShortener()

    documents = [
        Document(page_content=shortener.shorten_markdown(markdown))
        for markdown in packed_reviews
    ]

    summary_chain = load_summarize_chain(
        llm=llm,
        chain_type="map_reduce",
        map_prompt=map_prompt_template,
        combine_prompt=combine_prompt_template,
        token_max=30000,
        verbose=False,
        return_intermediate_steps=True,
    )

    result = summary_chain.invoke(
        {
            "company": target.company,
            "product": target.product,
            "input_documents": documents,
        }
    )

    result["output_text"] = shortener.unshorten_markdown(result["output_text"])
    log_summary_metrics(result["output_text"], "\n".join(packed_reviews))

    result["url_to_review"] = url_to_review

    return CustomerExperienceResult(**result)

def extract_app_store_urls(search_results: List[SearchResult]) -> Dict[str, Optional[str]]:
    """Helper to extract app store URLs from search results, compatible with the run function"""
    return {
        "apple_store_url": next(
            (
                result.link
                for result in search_results
                if apple_app_store.URL_PATTERN.match(result.link)
            ),
            None,
        ),
        "google_play_url": next(
            (
                result.link
                for result in search_results
                if google_play.URL_PATTERN.match(result.link)
            ),
            None,
        ),
        "steam_url": next(
            (
                result.link
                for result in search_results
                if steam.URL_PATTERN.match(result.link)
            ),
            None,
        ),
    }
