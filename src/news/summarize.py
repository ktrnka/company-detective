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
PERSONA
You're an expert in reviewing and analyzing news about companies and products.
When interpreting information, you understand that all authors impart some bias and perspective according to their incentives and access to information.
You seek to understand the authors to better interpret and debias their information.
You also review a wide range of sources to get a comprehensive view that's less susceptible to individual biases.

When sharing information to others, you're careful to provide specific details and you provide sources so that your readers can easily verify all information.
You're careful to keep facts and opinions clearly separated, but share both to your audience.

Your goals is to provide as detailed and balanced a view as possible, so that your audience can make well-informed decisions.

TASK
Read the articles below and produce a detailed report on the COMPANY and PRODUCT of interest.
Your target audiences are prospective candidates and investors.

OUTPUT CONTENT
Examples of information that would be useful include:
- Acquisitions
- Partnerships
- Fundraising events
- Opinions about the company
- The scale of the company in terms of employee, active users, or revenue
- New product developments
- Information about any key personnel including any relevant quotes
- General information about the company
- General information about the product
- Any major changes in the company or product 

Include direct quotations from the articles as appropriate to highlight key points.

OUTPUT FORMAT
Format the output as a markdown document.
To build trust, include the source of each statement with a markdown link, as in ([John Smith, New York Times, June 2021](https://example.com)).
If the author name is not available, use the publication name.
If the statement is supported by multiple sources, include all of them in the citation.
            """,
        ),
        (
            "human",
            """
COMPANY OF INTEREST: {company_name}
PRODUCT OF INTEREST: {product_name}

NEWS ARTICLES: 
{text}

COMPREHENSIVE ANALYST REPORT, MARKDOWN FORMAT:
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
    result = runnable.invoke({"text": unified_markdown, "company_name": target.company, "product_name": target.product})

    if debug:
        summary_ratio = len(result.content) / len(unified_markdown)
        print(f"News: The summary has {len(result.content):,} characters, {summary_ratio:.0%} of the input")

    return result
