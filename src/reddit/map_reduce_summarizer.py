from typing import List

from langchain_openai import ChatOpenAI

from core import CompanyProduct
import jinja2
from langchain_core.documents import Document
from langchain.chains.summarize import load_summarize_chain
from langchain import PromptTemplate

from praw.models import Submission

from .fetch import submission_to_markdown

# templates to convert summaries to markdown and html
templates = jinja2.Environment(
    loader=jinja2.FileSystemLoader("templates"),
)


def truncate_document(llm, document: str, max_tokens: int, debug=False) -> str:
    """Helper to truncate long documents"""
    num_tokens = llm.get_num_tokens(document)
    if num_tokens > max_tokens:
        approx_chars_per_token = len(document) / num_tokens
        num_chars_needed = max_tokens * approx_chars_per_token
        truncated_document = document[: int(num_chars_needed)]

        if debug:
            print(
                f"Truncated document from {num_tokens} tokens ({len(document)} chars) to {max_tokens} tokens ({len(truncated_document)} chars)"
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
- "quote" [Author, Reddit, Date](permalink)

For example:

Input comment:
## Comment ID hrmpl3t with +3 score by [MarketWorldly9908 on 2022-01-07](https://www.reddit.com/r/povertyfinance/comments/bg7ip2/internet_medicine_is_awesome_98point6_was_so_so/hrmpl3t/) (in reply to ID bg7ip2):
My husband and I have used 98.6 three times. All three times they did not prescribe the needed antibiotic to get better. I had an ear infection, my husband had an ear infection, then I had a sinus infection. We had to wait and get into our family doctor, so we paid 98.6 and our family doctor. I would not recommend them!

Example output:
- "All three times they did not prescribe the needed antibiotic to get better." [MarketWorldly9908, Reddit, 2022-01-07](https://www.reddit.com/r/povertyfinance/comments/bg7ip2/internet_medicine_is_awesome_98point6_was_so_so/hrmpl3t/)

Each quote should be a short, concise statement that captures the essence of the sentiment or information.
Be sure to extract a comprehensive sample of both positive and negative opinions, as well as any factual statements about the product.

REDDIT THREAD: 
{text}

MARKDOWN LIST OF QUOTES ABOUT THE COMPANY {company} AND PRODUCT {product}:
"""
map_prompt_template = PromptTemplate(template=map_prompt, input_variables=["text"])

combine_prompt = """
Please organize all of the quotes below into thematic topics of feedback about the COMPANY {company} and PRODUCT {product}.

Use the following top-level headings:
# Positive Sentiments
# Negative Sentiments
# Statements of Fact

If there are many quotes under a heading, please subdivide into headings to group similar quotes together.

Focus on selecting quotes that provide specific and grounded feedback. Avoid vague and general statements.

The output should be detailed and thorough, approximately 50% of the input length.

EXTRACTS FROM REDDIT THREADS: 
{text}

COMPREHENSIVE, ORGANIZED QUOTES IN MARKDOWN FORMAT:
"""
combine_prompt_template = PromptTemplate(
    template=combine_prompt, input_variables=["text", "company", "product"]
)


def summarize(target: CompanyProduct, threads: List[Submission], debug=True) -> dict:
    """Summarize a list of Reddit threads"""
    thread_markdowns = [submission_to_markdown(thread) for thread in threads]

    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

    truncated_thread_markdowns = [
        truncate_document(llm, document, 30000, debug=debug)
        for document in thread_markdowns
    ]
    documents = [
        Document(page_content=thread_markdown)
        for thread_markdown in truncated_thread_markdowns
    ]

    if debug:
        print(
            f"Reddit: The prompt context has {sum(len(doc.page_content) for doc in documents):,} characters in {len(documents)} threads"
        )

    summary_chain = load_summarize_chain(
        llm=llm,
        chain_type="map_reduce",
        map_prompt=map_prompt_template,
        combine_prompt=combine_prompt_template,
        token_max=30000,
        verbose=debug,
        return_intermediate_steps=True,
    )

    result = summary_chain.invoke(
        {
            "company": target.company,
            "product": target.product,
            "input_documents": documents,
        }
    )

    if debug:
        input_length = sum(len(doc.page_content) for doc in documents)
        intermediate_length = sum(
            len(text) for text in result["intermediate_steps"]
        )
        summary_length = len(result["output_text"])

        summary_input_ratio = summary_length / input_length
        summary_intermediate_ratio = summary_length / intermediate_length
        print(
            f"Reddit: The summary has {summary_length:,} characters, {summary_input_ratio:.0%} of the input, {summary_intermediate_ratio:.0%} of the intermediate extracts"
        )

    return result
