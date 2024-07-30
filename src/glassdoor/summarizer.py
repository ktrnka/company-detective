from typing import List
import jinja2
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages.ai import AIMessage


from core import CompanyProduct
from .scraper import GlassdoorReview

templates = jinja2.Environment(
    loader=jinja2.FileSystemLoader("templates"),
)

review_summary_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
            Please read the following Glassdoor reviews and write a summary of the key pros, cons, and quotations relating to the following aspects of the company:
            - Leadership
            - Compensation and benefits
            - Diversity, equity, and inclusion
            - Work-life balance
            - Growth opportunities
            - Company culture

            Please also include a section summarizing how the company has changed over time, if applicable.

            Please also summarize the relationship between job functions and employee satisfaction.

            Finish the summary with a list of questions that you would ask the company's leadership both following up on the reviews and also asking about topics that were not mentioned in the reviews.

            Provide a clear and concise summary of the key points, avoiding unnecessary details.
            Format the response as Markdown.

            In quotations please format like: "quote" (job title on date)
            """,
        ),
        (
            "human",
            """
            Company: {company}
            
            Glassdoor reviews: 
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

    print(f"The prompt context has {len(content_string):,} characters in {len(reviews)} reviews")

    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    runnable = review_summary_prompt | llm
    return runnable.invoke(
        {
            "text": content_string,
            "company": target.company,
        }
    )
