from typing import List
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages.ai import AIMessage
from langchain_openai import ChatOpenAI

from core import CompanyProduct
from dotenv import load_dotenv

load_dotenv()


prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
You're an expert in reviewing and analyzing news about companies and products.
You'll be given several articles to carefully review.
Produce a comprehensive summary of all the information about the company that might be useful for a prospective candidate or investor.
Examples of information that would be useful include:
- Acquisitions
- Partnerships
- Fundraising events
- Opinions about the company
- The scale of the company in terms of active users and/or revenue
- New product developments
- The names and roles of any key personnel

Format the output as a markdown document.
When summarizing a claim, reference the source of the claim with a markdown link, as in ([John Smith, New York Times, June 2021](https://example.com)).
If the author name is not available, use the publication name.
            """,
        ),
        (
            "human",
            """
COMPANY OF INTEREST: {company_name}

NEWS ARTICLES: 
{text}

COMPREHENSIVE SUMMARY, MARKDOWN FORMAT:
            """,
        ),
    ]
)


def summarize(
    target: CompanyProduct, article_markdowns: List[str], debug=True
) -> AIMessage:
    """Summarize a list of news articles"""
    unified_markdown = "\n\n".join(article for article in article_markdowns)

    if debug:
        print(f"News: {len(unified_markdown):,} characters of context, {len(article_markdowns)} articles")

    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

    runnable = prompt | llm
    result = runnable.invoke({"text": unified_markdown, "company_name": target.company})

    return result
