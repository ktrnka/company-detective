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
You're an expert in reviewing and summarizing news about companies and products.
You'll be given several articles about a company in markdown format.
Produce a unified summary of all the information about the company that might be useful for a prospective candidate or investor.
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
If the author name is not available, just use the publication name.

At the end of the document, include a list of the sources that were used to generate the summary. For each article, include:
- The author
- The publication date
- The title
- A link to the article
- The organization that published the article
            """,
        ),
        (
            "human",
            """
            Company: {company_name}
            
            Articles: 
            {text}
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
        print(f"{len(unified_markdown):,} characters in unified context")

    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

    runnable = prompt | llm
    result = runnable.invoke({"text": unified_markdown, "company_name": target.company})

    return result
