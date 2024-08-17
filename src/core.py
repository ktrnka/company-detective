from typing import NamedTuple
import re
import os
from datetime import datetime, timedelta
from langchain.globals import set_llm_cache
from langchain.cache import SQLiteCache
import requests_cache


class CompanyProduct(NamedTuple):
    company: str
    product: str

    @classmethod
    def same(cls, name: str):
        return cls(company=name, product=name)


assert CompanyProduct.same("98point6")


def make_experiment_dir(target: CompanyProduct) -> str:
    folder_name = re.sub(r"[^a-zA-Z0-9]", "_", f"{target.company} {target.product}")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    folder_path = f"experiments/{folder_name}/{timestamp}"

    os.makedirs(folder_path, exist_ok=True)

    return folder_path


def get_project_dir(relative_path: str, create_if_needed=True) -> str:
    """Get the path of a file from the project root"""
    current_file = os.path.abspath(__file__)
    project_root = os.path.dirname(os.path.dirname(current_file))
    project_dir = os.path.join(project_root, relative_path)

    if create_if_needed:
        os.makedirs(project_dir, exist_ok=True)

    return project_dir


def init_langchain_cache():
    """Initialize the langchain cache, which improves speed and cost of the LLM by caching in SQLite"""
    cache_dir = get_project_dir(".cache")
    cache_path = os.path.join(cache_dir, "langchain.sqlite")

    set_llm_cache(SQLiteCache(database_path=cache_path))

    return cache_path


def init_requests_cache():
    """Initialize the requests cache, which improves the speed of the requests library by caching in SQLite and should reduce risk around getting blocked"""
    cache_dir = get_project_dir(".cache")
    cache_path = os.path.join(cache_dir, "requests_cache.sqlite")

    requests_cache.install_cache(
        cache_path, backend="sqlite", expire_after=timedelta(days=7), allowable_codes=[200, 403]
    )

    # I originally tried cache_control=True but many news sites disable caching entirely which isn't what I want during development

    # TODO: There's a design limitation in how this interacts with throttling, like in the news article scraper. Though the news article scraper also does a lru in-memory cache, so it only matters on fresh notebooks.

    return cache_path



import re

def nest_markdown(markdown_doc: str, header_change: int) -> str:
    """Nest the headers in a markdown document by changing the header level"""
    assert header_change > 0, "Header change must be positive"
    nested_markdown = re.sub(r'^(#+)', lambda match: '#' * min(len(match.group(1)) + header_change, 6), markdown_doc, flags=re.MULTILINE)
    return nested_markdown

def test_nest_markdown():
    # Test nest_markdown function
    markdown_doc = """
    # Header 1
    Some text

    ## Header 2

    This # might be harder
    """
    header_change = 2

    expected_output = """
    ### Header 1
    Some text

    #### Header 2

    This # might be harder
    """

    # Check if the nested markdown is correct
    assert nest_markdown(markdown_doc, header_change) == expected_output, f"Expected: \n{expected_output}\n\nActual: \n{nest_markdown(markdown_doc, header_change)}"
