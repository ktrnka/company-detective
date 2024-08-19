from typing import List
from core import CompanyProduct, cleanse_markdown, extract_suspicious_urls, extractive_fraction, extractive_fraction_urls, num_cache_mentions
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
You're an expert at organizing and filtering search results.
Given search results for a company or product, filter out less useful pages and organize the interesting ones into the following headers:

# Official social media
Include links to official social media profiles (e.g., Twitter, LinkedIn, Facebook).

# Job boards
Include unique job board pages (exclude clones and low-quality sites).

# App stores
Include links to app store pages (e.g., Google Play, Apple App Store).

# Product reviews
Include detailed and reputable product reviews (e.g., major review sites, detailed user reviews).

# News articles (most recent first, grouped by event)
Include significant news articles, especially from reputable sources. Group by event and date.

# Key employees (grouped by employee)
Include profiles and articles related to key employees (e.g., LinkedIn profiles, interviews, blog posts).

# Other pages on the company website
Include relevant pages from the company's official website (e.g., about, contact, blog, case studies).

# Other
Include any other relevant and useful pages that do not fit into the above categories, grouped by type.

Exclude:
- Low-quality job boards and clones (e.g., clones of Indeed, Glassdoor, Crunchbase).
- Irrelevant results not directly related to the company or product.
- Duplicate or near-duplicate content.
- Low-quality or spammy pages.

Useful content guidelines:
- Partnership Articles: Articles from the websites of partner companies or government organizations about their partnership with the company. These provide third-party evidence about the company.
- Investor Articles: Articles from investors in the company, as these investors have contributed significant funding and likely performed extensive diligence.
- Reputable Sources: Information from well-known and trustworthy sources such as the Better Business Bureau (BBB), which provides reliable complaints and reviews about companies.
- Older News: Older news articles that provide historical context or significant past events related to the company.
- Interviews and Podcasts: Interviews and podcasts featuring key employees or stakeholders. These formats often provide more in-depth insights and perspectives than general news articles because they allow for a deeper understanding of the individuals and their approach to work. They can reveal both positive and negative aspects of the people involved due to their longer and less edited nature.
- Case Studies: Detailed case studies or success stories from other companies highlighting their use of the company's products or services.
- App Store Reviews: Reviews and ratings from app stores, as these reflect real user experiences and feedback.

Formatting:
- Include the publication date after the link, if available.
- Order the results in each section from most to least relevant unless otherwise specified.
- Format the output as a markdown document, preserving any links from the input. Preserve the exact URI from the original search result.

Use these criteria to effectively filter and organize the search results into the specified headers.
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
    logger.info("Extractive fraction: {:.0%}", extractive_fraction(result.content, unified_markdown))
    logger.info("Percent of URLs in sources: {:.0%}", extractive_fraction_urls(result.content, unified_markdown))
    logger.info("Suspicious URLs: {}", extract_suspicious_urls(result.content, unified_markdown))
    logger.info("Cache mentions: {} (should be zero)", num_cache_mentions(result.content))


    return result
