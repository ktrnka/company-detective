from typing import List

import jinja2
from langchain_core.documents import Document
from langchain.chains.summarize import load_summarize_chain
from langchain import PromptTemplate
from langchain_openai import ChatOpenAI
from praw.models import Submission
from pydantic import BaseModel
from loguru import logger

from core import CompanyProduct, URLShortener, log_summary_metrics
from .fetch import submission_to_markdown


# templates to convert summaries to markdown and html
templates = jinja2.Environment(
    loader=jinja2.FileSystemLoader("templates"),
)


class SummaryResult(BaseModel):
    """Wrapper around the summarization chain with intermediate steps returned"""

    output_text: str
    intermediate_steps: List[str]

    # Note: This can't be automatically deserialized because of the Document type, but the error is a cryptic one about the number of args to validate
    # input_documents: List[Document]


def truncate_document(llm, document: str, max_tokens: int) -> str:
    """Helper to truncate long documents"""
    num_tokens = llm.get_num_tokens(document)
    if num_tokens > max_tokens:
        approx_chars_per_token = len(document) / num_tokens
        num_chars_needed = max_tokens * approx_chars_per_token
        truncated_document = document[: int(num_chars_needed)]

        logger.debug(
            "Truncated document from {:,} tokens ({:,} chars) to {:,} tokens ({:,}) chars)",
            num_tokens,
            len(document),
            max_tokens,
            len(truncated_document),
        )

        return truncated_document
    else:
        return document


map_prompt = """
Please read the following Reddit thread and extract all opinions and facts relating to the user experience of the PRODUCT {product} by the COMPANY {company} from the perspective of current users.
Only include information about the COMPANY {company} and PRODUCT {product}. 
Do not extract information about other companies or products.
If the text does not contain any relevant information about the COMPANY or PRODUCT, please return an empty string.

Format the results as a Markdown list of quotes, each with a permalink to the source of the quote like so:
- "quote" [Author, Reddit, Date](url)

EXAMPLE for 98point6:

Input comment:
## Comment ID hrmpl3t with +3 score by [MarketWorldly9908 on 2022-01-07](cache://reddit/42) (in reply to ID bg7ip2):
My husband and I have used 98.6 three times. All three times they did not prescribe the needed antibiotic to get better. I had an ear infection, my husband had an ear infection, then I had a sinus infection. We had to wait and get into our family doctor, so we paid 98.6 and our family doctor. I would not recommend them!

Example output:
- "All three times they did not prescribe the needed antibiotic to get better." [MarketWorldly9908, Reddit, 2022-01-07](cache://reddit/42)

----

Each quote should be a short, concise statement that captures the essence of the sentiment or information.
Be sure to extract a comprehensive sample of both positive and negative opinions, as well as any factual statements about the product.

REDDIT THREAD: 
{text}

MARKDOWN LIST OF QUOTES ABOUT THE COMPANY {company} AND PRODUCT {product} (markdown only, don't wrap in backticks):
"""
map_prompt_template = PromptTemplate(template=map_prompt, input_variables=["text"])

combine_prompt = """
Please organize all of the quotes below into topics about the COMPANY {company} and PRODUCT {product}.
Organize into headings based on the sentiment or type of information in the quote.

EXTRACTS FROM REDDIT THREADS: 
{text}

ORGANIZED QUOTES IN MARKDOWN FORMAT (markdown only, don't wrap in backticks):
"""
combine_prompt_template = PromptTemplate(
    template=combine_prompt, input_variables=["text", "company", "product"]
)


def summarize(target: CompanyProduct, threads: List[Submission]) -> SummaryResult:
    """Summarize a list of Reddit threads"""
    thread_markdowns = [submission_to_markdown(thread) for thread in threads]
    url_shortener = URLShortener()

    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

    truncated_thread_markdowns = [
        truncate_document(llm, document, 30000) for document in thread_markdowns
    ]
    documents = [
        Document(page_content=url_shortener.shorten_markdown(thread_markdown))
        for thread_markdown in truncated_thread_markdowns
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
    result["output_text"] = url_shortener.unshorten_markdown(result["output_text"])

    result = SummaryResult(**result)

    input_length = sum(len(doc) for doc in truncated_thread_markdowns)
    intermediate_length = sum(len(text) for text in result.intermediate_steps)
    summary_length = len(result.output_text)

    logger.info(
        "Reddit: Extract stage {:,} chars -> {:,} chars ({:.0%})",
        input_length,
        intermediate_length,
        intermediate_length / input_length,
    )
    logger.info(
        "Reddit: Combine stage {:,} chars -> {:,} chars ({:.0%})",
        intermediate_length,
        summary_length,
        summary_length / intermediate_length,
    )

    # Smoke tests
    unshortened_context = "\n\n".join(thread_markdowns)
    log_summary_metrics(result.output_text, unshortened_context)

    return result
