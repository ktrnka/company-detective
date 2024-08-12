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
Please read the following Reddit thread and extract key opinions and facts relating to the user experience of the PRODUCT {product} by the COMPANY {company} from the perspective of current users.
Only include information about the COMPANY {company} and PRODUCT {product}. 
Do not extract information about other companies or products.
If the text does not contain any relevant information about the COMPANY or PRODUCT, please write "No relevant information found."

Format the results as a Markdown list of quotes, each with a permalink to the source of the quote like so:
- "quote" [Author on Date](permalink)

For example:

Input comment:
## Comment ID hrmpl3t with +3 score by [MarketWorldly9908 on 2022-01-07](https://www.reddit.com/r/povertyfinance/comments/bg7ip2/internet_medicine_is_awesome_98point6_was_so_so/hrmpl3t/) (in reply to ID bg7ip2):
My husband and I have used 98.6 three times. All three times they did not prescribe the needed antibiotic to get better. I had an ear infection, my husband had an ear infection, then I had a sinus infection. We had to wait and get into our family doctor, so we paid 98.6 and our family doctor. I would not recommend them!

Example output:
- "All three times they did not prescribe the needed antibiotic to get better." [MarketWorldly9908 on 2022-01-07](https://www.reddit.com/r/povertyfinance/comments/bg7ip2/internet_medicine_is_awesome_98point6_was_so_so/hrmpl3t/)

Each quote should be a short, concise statement that captures the essence of the sentiment or information.
Be sure to extract a comprehensive sample of both positive and negative opinions, as well as any factual statements about the product.

Reddit thread: 
{text}

MARKDOWN LIST OF QUOTES ABOUT THE COMPANY AND PRODUCT:
"""
map_prompt_template = PromptTemplate(template=map_prompt, input_variables=["text"])

combine_prompt = """
Please cluster all of the quotes below, organizing them into thematic topics of feedback about the COMPANY {company} and PRODUCT {product}.
Use the following top-level headings:
# Positive Sentiments
# Negative Sentiments
# Statements of Fact

If there are many quotes under a heading, please subdivide into headings to group similar quotes together.

Summaries: 
{text}


GROUPED QUOTES IN MARKDOWN FORMAT:
"""
combine_prompt_template = PromptTemplate(
    template=combine_prompt, input_variables=["text"]
)


def summarize(target: CompanyProduct, threads: List[Submission], debug=False) -> str:
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

    summary_chain = load_summarize_chain(
        llm=llm,
        chain_type="map_reduce",
        map_prompt=map_prompt_template,
        combine_prompt=combine_prompt_template,
        token_max=30000,
        verbose=debug,
    )

    output = summary_chain.run(
        {
            "company": target.company,
            "product": target.product,
            "input_documents": documents,
        }
    )

    return output
