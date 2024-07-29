from typing import Optional, List
from langchain_core.pydantic_v1 import BaseModel, Field
from typing import NamedTuple
from langchain_core.messages.ai import AIMessage
import markdown
from itertools import chain
import hashlib
import os

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from core import CompanyProduct
import jinja2
import praw

templates = jinja2.FileSystemLoader("templates")

class Claim(BaseModel):
    """A claim made in a Reddit thread"""

    quote: str = Field(
        description="A short quote from the source representing the key claim"
    )
    comment_id: str = Field(description="The comment ID of the quote")


class ThreadSummary(BaseModel):
    """A structured summary of a Reddit thread or threads about a company or product"""

    thread_summary: str = Field(description="An overview of the content")

    user_experience_strengths: Optional[List[Claim]] = Field(
        default=None,
        description="Key positive themes in user feedback about the product",
    )
    user_experience_weaknesses: Optional[List[Claim]] = Field(
        default=None,
        description="Key negative themes in user feedback about the product",
    )

    employee_experience_strengths: Optional[List[Claim]] = Field(
        default=None,
        description="The key strengths of the company from the employee perspective",
    )
    employee_experience_weaknesses: Optional[List[Claim]] = Field(
        default=None,
        description="The key weaknesses of the company from the employee perspective",
    )

    investor_perspective: Optional[List[Claim]] = Field(
        default=None,
        description="Key information about the company from the perspective of a prospective investor",
    )


json_instructions = """
The JSON object should have these top-level keys:

Required:
thread_summary (string): An overview of the content discussed in the Reddit thread(s).

Optional (should be omitted if no information is available):
user_experience_strengths (list of Claim objects): Key positive themes in user feedback about the product.
user_experience_weaknesses (list of Claim objects): Key negative themes in user feedback about the product.
employee_experience_strengths (list of Claim objects): Key strengths of the company from the employee perspective.
employee_experience_weaknesses (list of Claim objects): Key weaknesses of the company from the employee perspective.
investor_perspective (list of Claim objects): Key information about the company from the perspective of a prospective investor.
Each Claim object should match this format:

Claim Object:
quote (string): A short quote from the source representing the key claim.
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
            Then it should three sections summarizing key facts and opinions from different perspectives:
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
            COMPANY: {company}
            PRODUCT: {product}
            
            Reddit thread: 
            {text}
            """
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
            """
            ),
    ]
)

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

def wrap_html(content: str):
    return f"""
<html>
<body>
    {content}
</body>
</html>
"""


def claims_to_html(claims: Optional[List[Claim]]) -> str:
    if not claims:
        return ""

    return (
        "<ul>"
        + "\n".join(
            f'<li>"{claim.quote}" (source: {claim.comment_id})</li>' for claim in claims
        )
        + "</ul>"
    )


class Evaluation(NamedTuple):
    claims_made: int
    quotes_in_source: int
    comment_ids_in_source: int


class ThreadResult(NamedTuple):
    submission: praw.models.Submission
    text: str
    summary_result: AIMessage

    def evaluate(self) -> Evaluation:
        claims_made = 0
        quotes_in_source = 0
        comment_ids_in_source = 0

        for claim in chain(
            self.summary_result.user_experience_strengths or [],
            self.summary_result.user_experience_weaknesses or [],
            self.summary_result.employee_experience_strengths or [],
            self.summary_result.employee_experience_weaknesses or [],
            self.summary_result.investor_perspective or [],
        ):

            claims_made += 1

            # NOTE: I reviewed one that had 4/12 quotes and 12/12 comment_ids and found that the quotes were correct but some slightly changed the case or cut out a ... or added a "The" at the beginning. I should re-assess on other documents though.
            if claim.quote in self.text:
                quotes_in_source += 1

            if claim.comment_id in self.text:
                comment_ids_in_source += 1

        return Evaluation(claims_made, quotes_in_source, comment_ids_in_source)

    def to_html(self):
        summary_content = self.summary_result

        # Note: This was refactored to work properly with the structured output format

        return f"""
<h1>{self.submission.title} by {self.submission.author} on {utc_to_date(self.submission.created_utc)}</h1>
<a href="{self.submission.url}">{self.submission.url}</a>

{summary_content.thread_summary}

<h2>User Experience</h2>

<h3>Strengths</h3>

{claims_to_html(summary_content.user_experience_strengths)}

<h3>Weaknesses</h3>

{claims_to_html(summary_content.user_experience_weaknesses)}

<h2>Employee Experience</h2>

<h3>Strengths</h3>

{claims_to_html(summary_content.employee_experience_strengths)}

<h3>Weaknesses</h3>

{claims_to_html(summary_content.employee_experience_weaknesses)}

<h2>Investor Perspective</h2>

{claims_to_html(summary_content.investor_perspective)}

<h2>Original Thread</h2>
<p>{markdown.markdown(self.text)}</p>
        """


class AggregationResult(NamedTuple):
    # inputs
    target: CompanyProduct
    summaries: List[ThreadResult]
    aggregation_prompt_context: str

    # outputs
    summary_result: AIMessage

    def evaluate(self) -> Evaluation:
        claims_made = 0
        quotes_in_source = 0
        comment_ids_in_source = 0

        for claim in chain(
            self.summary_result.user_experience_strengths or [],
            self.summary_result.user_experience_weaknesses or [],
            self.summary_result.employee_experience_strengths or [],
            self.summary_result.employee_experience_weaknesses or [],
            self.summary_result.investor_perspective or [],
        ):

            claims_made += 1

            if claim.quote in self.aggregation_prompt_context:
                quotes_in_source += 1

            if claim.comment_id in self.aggregation_prompt_context:
                comment_ids_in_source += 1

        return Evaluation(claims_made, quotes_in_source, comment_ids_in_source)

    def to_html(self):
        summary_content = self.summary_result

        # Note: This was refactored to work properly with the structured output format

        return f"""
<h1>{self.target.company} / {self.target.product}</h1>

{summary_content.thread_summary}

<h2>User Experience</h2>

<h3>Strengths</h3>

{claims_to_html(summary_content.user_experience_strengths)}

<h3>Weaknesses</h3>

{claims_to_html(summary_content.user_experience_weaknesses)}

<h2>Employee Experience</h2>

<h3>Strengths</h3>

{claims_to_html(summary_content.employee_experience_strengths)}

<h3>Weaknesses</h3>

{claims_to_html(summary_content.employee_experience_weaknesses)}

<h2>Investor Perspective</h2>

{claims_to_html(summary_content.investor_perspective)}
        """


def summarize_thread(
    target: CompanyProduct, url: str, text_max_chars=40000
) -> ThreadResult:
    submission = reddit.submission(url=url)
    text = format_reddit_thread(submission)

    if len(text) > text_max_chars:
        print(f"Text too long: {len(text)} > {text_max_chars}. Truncating.")
        text = text[:text_max_chars]

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
    return ThreadResult(submission=submission, text=text, summary_result=summary_result)


def claims_to_markdown(claims: Optional[List[Claim]]) -> str:
    if not claims:
        return "Not applicable"

    return "\n".join(
        f'- "{claim.quote}" (source: {claim.comment_id})' for claim in claims
    )


def summary_to_markdown(summary_result: ThreadResult, debug=False) -> str:
    text = f"""
# Summary: {summary_result.submission.title} (thread id: {summary_result.submission.id})

{summary_result.summary_result.thread_summary}

## User Experience

### Strengths

{claims_to_markdown(summary_result.summary_result.user_experience_strengths)}

### Weaknesses

{claims_to_markdown(summary_result.summary_result.user_experience_weaknesses)}

## Employee Experience

### Strengths

{claims_to_markdown(summary_result.summary_result.employee_experience_strengths)}

### Weaknesses

{claims_to_markdown(summary_result.summary_result.employee_experience_weaknesses)}

## Investor Perspective

{claims_to_markdown(summary_result.summary_result.investor_perspective)}
    """

    if debug:
        text += f"""
## Debug

### Original Thread
{summary_result.text}
        """

    return text


def summarize_summaries(
    target: CompanyProduct, summaries: List[ThreadResult]
) -> AggregationResult:
    text = "\n\n".join(summary_to_markdown(result) for result in summaries)

    runnable = aggregation_prompt | llm.with_structured_output(schema=ThreadSummary)
    result = runnable.invoke(
        {
            "text": text,
            "company": target.company,
            "product": target.product,
            "json_instructions": json_instructions,
        }
    )

    return AggregationResult(
        target=target,
        summaries=summaries,
        aggregation_prompt_context=text,
        summary_result=result,
    )


def summarize_prompt(prompt):
    return f"""
<h1>Prompt</h1>

<h2>System prompt</h2>
<pre>
{prompt.messages[0].prompt.template}
</pre>

<h2>Prompt</h2>
<pre>
{prompt.messages[1].prompt.template}
</pre>
    """


def short_evaluation(target: CompanyProduct, num_threads=2):
    # This is cached so it should be quick
    thread_urls = reddit_search(target, stop=10, pause=2)[:num_threads]

    # The ID of the test is the last 4 chars of the sha of the url list
    test_id = hashlib.sha256("".join(thread_urls).encode()).hexdigest()[-4:]

    folder = f"evaluation/test_{test_id}"
    os.makedirs(folder, exist_ok=True)

    # individual thread results
    results = [summarize_thread(target, url) for url in thread_urls]

    # aggregation result
    aggregation_result = summarize_summaries(target, results)

    # make a unified page
    result_htmls = "\n".join(r.to_html() for r in results)
    html_result = wrap_html(
        f"""
{aggregation_result.to_html()}

<hr/>

<h1>Debugging the aggregation</h1>

<h2>Hallucination evaluation</h2>
Note: This only evaluates the evaluation stage, not the mapping stage.
{aggregation_result.evaluate()}

<h2>Aggregation prompt</h2>
{summarize_prompt(aggregation_prompt)}

<h2>Aggregation input (converted markdown to HTML)</h2>
{markdown.markdown(aggregation_result.aggregation_prompt_context)}

<hr/>

<h1>Debugging the mapping</h1>

<h2>Mapping prompt</h2>

{summarize_prompt(thread_summary_prompt)}


<h2>Individual summaries</h2>
{result_htmls}
"""
    )

    # Create the filename using the current timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{folder}/{timestamp}.html"

    with open(filename, "w") as f:
        f.write(html_result)

    print(f"Results for {target} saved to {filename}")
