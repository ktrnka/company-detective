from typing import Optional, List
from langchain_core.pydantic_v1 import BaseModel, Field
from typing import NamedTuple
from langchain_core.messages.ai import AIMessage
from itertools import chain

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from core import CompanyProduct
import jinja2
import praw

from praw.models import Submission

from .fetch import submission_to_markdown

# templates to convert summaries to markdown and html
templates = jinja2.Environment(
    loader=jinja2.FileSystemLoader("templates"),
)


class Claim(BaseModel):
    """A claim made in a Reddit thread"""

    quote: str = Field(
        description="A short quote from the source representing the key claim about the COMPANY or PRODUCT"
    )
    comment_id: str = Field(description="The comment or post ID of the quote")


class ThreadSummary(BaseModel):
    """A structured summary of a Reddit thread or threads about a COMPANY or PRODUCT"""

    thread_summary: str = Field(description="An overview of the content")

    user_experience_strengths: Optional[List[Claim]] = Field(
        default=None,
        description="Key positive themes in user feedback about the PRODUCT",
    )
    user_experience_weaknesses: Optional[List[Claim]] = Field(
        default=None,
        description="Key negative themes in user feedback about the PRODUCT",
    )

    employee_experience_strengths: Optional[List[Claim]] = Field(
        default=None,
        description="The key strengths of the COMPANY from the employee perspective",
    )
    employee_experience_weaknesses: Optional[List[Claim]] = Field(
        default=None,
        description="The key weaknesses of the COMPANY from the employee perspective",
    )

    investor_perspective: Optional[List[Claim]] = Field(
        default=None,
        description="Key information about the COMPANY from the perspective of a prospective investor",
    )


# Note: To update this, run ThreadSummary.schema() and feed it into ChatGPT with this example output
json_instructions = """
The JSON object should have these top-level keys:

Required:
thread_summary (string): An overview of the content discussed in the Reddit thread(s).

Optional (should be omitted if no information is available):
user_experience_strengths (list of Claim objects): Key positive themes in user feedback about the PRODUCT.
user_experience_weaknesses (list of Claim objects): Key negative themes in user feedback about the PRODUCT.
employee_experience_strengths (list of Claim objects): Key strengths of the COMPANY from the employee perspective.
employee_experience_weaknesses (list of Claim objects): Key weaknesses of the COMPANY from the employee perspective.
investor_perspective (list of Claim objects): Key information about the COMPANY from the perspective of a prospective investor.

Each Claim object should match this format:

Claim Object:
quote (string): A short quote from the source representing the statement of experience, fact, or opinion about the COMPANY or PRODUCT.
comment_id (string): The comment ID of the quote.
"""


# See also
# https://www.reddit.com/r/ChatGPT/comments/11twe7z/prompt_to_summarize/
# https://www.reddit.com/r/ChatGPT/comments/13na8yp/highly_effective_prompt_for_summarizing_gpt4/

thread_summary_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
            Please read the following Reddit thread and write an evididence-based summary of the key points relating to the COMPANY and PRODUCT specified.
            The summary should begin with a brief 1-2 sentence summary of the thread.
            Then it should three sections summarizing key facts and opinions about the COMPANY or PRODUCT from different perspectives:
            1. User experience perspective: The key strengths and weaknesses of the PRODUCT from the perspective of current users.
            2. Prospective employee perspective: The key strengths and weaknesses of the COMPANY from the perspective of employees. For example this could include information about the benefits, company culture, work-life balance, or other relevant information.
            3. Prospective investor perspective: Any key information about the COMPANY from the perspective of a prospective investor, such as fundraising, valuation, layoffs, partnerships, or other information indicating that the company is improving or worsening. 

            Provide a clear and concise summary of the key points, avoiding unnecessary details.
            Do not make speculations, simply summarize the key facts and opinions stated in the thread.
            
            Limit the response to 5000 tokens.
            Format the results as Json in the following format:
            {json_instructions}
            """,
        ),
        (
            "human",
            """
            Only include information about the COMPANY {company} and PRODUCT {product}. Do not extract information about other companies or products.
            
            Reddit thread: 
            {text}
            """,
        ),
    ]
)

aggregation_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
            Please read the following summaries of Reddit threads and write a comprehensive summary of the key points relating to the COMPANY and PRODUCT specified.

            The summary should begin with an overview paragraph.

            Then it should three sections summarizing key facts and opinions from different perspectives:
            1. User experience perspective: The key strengths and weaknesses of the PRODUCT from the perspective of current users.
            2. Prospective employee perspective: The key strengths and weaknesses of the COMPANY from the perspective of employees. For example this could include information about the benefits, company culture, work-life balance, or other relevant information. 
            3. Prospective investor perspective: Any key information about the COMPANY from the perspective of a prospective investor, such as fundraising, valuation, layoffs, partnerships, or other information indicating that the company is improving or worsening. 

            Do not make speculations, simply summarize the key facts and opinions stated in the thread.
            Limit the response to 5000 tokens.
            Format the results as Json in the following format:
            {json_instructions}
            """,
        ),
        (
            "human",
            """
            COMPANY: {company}
            PRODUCT: {product}
            
            Summaries: 
            {text}
            """,
        ),
    ]
)


class Evaluation(NamedTuple):
    claims_made: int
    quotes_in_source: int
    comment_ids_in_source: int


def evaluate_claims(result: AIMessage, text: str) -> Evaluation:
    claims_made = 0
    quotes_in_source = 0
    comment_ids_in_source = 0

    for claim in chain(
        result.user_experience_strengths or [],
        result.user_experience_weaknesses or [],
        result.employee_experience_strengths or [],
        result.employee_experience_weaknesses or [],
        result.investor_perspective or [],
    ):
        claims_made += 1

        # NOTE: I reviewed one that had 4/12 quotes and 12/12 comment_ids and found that the quotes were correct but some slightly changed the case or cut out a ... or added a "The" at the beginning. I should re-assess on other documents though.
        if claim.quote in text:
            quotes_in_source += 1

        if claim.comment_id in text:
            comment_ids_in_source += 1

    return Evaluation(claims_made, quotes_in_source, comment_ids_in_source)


class ThreadSummaryResult(NamedTuple):
    # inputs
    submission: praw.models.Submission
    text: str

    # outputs
    summary_result: AIMessage

    def evaluate(self) -> Evaluation:
        return evaluate_claims(self.summary_result, self.text)

    def is_under_max_hallucinations(
        self, max_allowable_hallucinations: int, debug=False
    ) -> bool:
        """
        Check for hallucinations using the comment_id evaluation, which seems pretty reliable.
        """
        evaluation = self.evaluate()
        is_ok = (
            evaluation.claims_made - evaluation.comment_ids_in_source
            <= max_allowable_hallucinations
        )

        if debug and not is_ok:
            print(f"Filtering {self.submission.title} with evaluation {evaluation}")

        return is_ok

    def to_markdown(self):
        template = templates.get_template("thread_summary.md")
        return template.render(
            result=self,
        )

    def to_html(self, permalinks=None):
        template = templates.get_template("thread_summary.html")
        return template.render(
            result=self,
            permalinks=permalinks,
        )


class AggregatedSummaryResult(NamedTuple):

    # inputs
    target: CompanyProduct
    summaries: List[ThreadSummary]
    aggregation_prompt_context: str

    # outputs
    summary_result: AIMessage

    def evaluate(self) -> Evaluation:
        return evaluate_claims(self.summary_result, self.aggregation_prompt_context)

    def to_markdown(self):
        template = templates.get_template("thread_group_summary.md")
        return template.render(
            result=self,
        )

    def to_html(self, permalinks=None):
        template = templates.get_template("thread_group_summary.html")
        return template.render(
            result=self,
            permalinks=permalinks,
        )


def summarize_submission(
    target: CompanyProduct, submission: Submission, text_max_chars=40000
) -> ThreadSummaryResult:
    """
    Create a structured summary of a Reddit submission about a company or product
    """
    text = submission_to_markdown(submission)

    # TODO: Replace truncation with splitting the content in some form. Also replace with a token limit rather than a character limit.
    if len(text) > text_max_chars:
        print(f"Text too long: {len(text)} > {text_max_chars}. Truncating.")
        text = text[:text_max_chars]

    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    runnable = thread_summary_prompt | llm.with_structured_output(
        schema=ThreadSummary, method="json_mode"
    )
    summary_result = runnable.invoke(
        {
            "text": text,
            "company": target.company,
            "product": target.product,
            "json_instructions": json_instructions,
        }
    )
    return ThreadSummaryResult(
        submission=submission, text=text, summary_result=summary_result
    )


def summarize_summaries(
    target: CompanyProduct, summaries: List[ThreadSummaryResult]
) -> AggregatedSummaryResult:
    text = "\n\n".join(result.to_markdown() for result in summaries)

    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    runnable = aggregation_prompt | llm.with_structured_output(schema=ThreadSummary)
    result = runnable.invoke(
        {
            "text": text,
            "company": target.company,
            "product": target.product,
            "json_instructions": json_instructions,
        }
    )

    return AggregatedSummaryResult(
        target=target,
        summaries=summaries,
        aggregation_prompt_context=text,
        summary_result=result,
    )


# TODO: Remove or replace this
def summarize_prompt(prompt: ChatPromptTemplate) -> str:
    template = templates.get_template("prompt.html")
    return template.render(prompt=prompt)
