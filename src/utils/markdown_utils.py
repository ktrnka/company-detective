import re
from typing import Set


CACHE_LINK_PATTERN = re.compile(r"\[([^\]]+)\]\(cache://([^\)]+)\)")


def strip_cache_links(markdown: str) -> str:
    return CACHE_LINK_PATTERN.sub(r"\1", markdown)


def test_strip_cache_links():
    assert strip_cache_links("") == ""

    # Don't strip normal links
    assert strip_cache_links("cache://example.com") == "cache://example.com"

    # Don't strip non-cache MD links
    assert (
        strip_cache_links("[example](http://example.com)")
        == "[example](http://example.com)"
    )

    # Strip cache MD links
    assert strip_cache_links("[example](cache://example.com)") == "example"

    # Strip it even if it's in citation format
    assert (
        strip_cache_links("[(example, 2019)](cache://example.com)") == "(example, 2019)"
    )


def nest_markdown(markdown_doc: str, header_change: int) -> str:
    """Nest the headers in a markdown document by changing the header level"""
    assert header_change > 0, "Header change must be positive"
    nested_markdown = re.sub(
        r"^(#+)",
        lambda match: "#" * min(len(match.group(1)) + header_change, 6),
        markdown_doc,
        flags=re.MULTILINE,
    )
    return nested_markdown


def test_nest_markdown():
    """Test the nest_markdown function"""
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
    assert (
        nest_markdown(markdown_doc, header_change) == expected_output
    ), f"Expected: \n{expected_output}\n\nActual: \n{nest_markdown(markdown_doc, header_change)}"


def extract_urls(markdown: str) -> Set[str]:
    # NOTE: This will extract any markdown URLs like [...](...) regardless of scheme
    linked_urls = re.findall(r"\[[^]]+\]\(([^)\]]+)\)", markdown)

    # NOTE: This will extract any URLs in general, but only http and https
    bare_urls = re.findall(r"(https?://[^\s)\]]+)", markdown)

    return set(linked_urls).union(bare_urls)


def test_extract_urls():
    assert sorted(extract_urls("[a](b) [c](d)")) == ["b", "d"]

    # Sometimes the LLM mangles the Markdown and we ignore those
    assert sorted(extract_urls("[a](b) [c](d [e](f)")) == ["b", "f"]

    # TDD for new functionality: Extracting URLs that aren't markdown links
    assert sorted(extract_urls("https://www.example.com")) == [
        "https://www.example.com"
    ]

    assert sorted(extract_urls("[a](b) [c](d [e](https://www.example.com)")) == [
        "b",
        "https://www.example.com",
    ]


def fix_markdown_list(markdown_text: str) -> str:
    fixed_text = re.sub(
        r"^([^-\n][^\n]*\n)(-)", r"\1\n\2", markdown_text, flags=re.MULTILINE
    )
    return fixed_text


def test_fix_markdown_list():
    example_incorrect_markdown_list = """
This needs a newline after it:
- One
- Two

This one is ok:

- Three
- Four
"""

    fixed_example_incorrect_markdown_list = """
This needs a newline after it:

- One
- Two

This one is ok:

- Three
- Four
"""
    assert (
        fix_markdown_list(example_incorrect_markdown_list)
        == fixed_example_incorrect_markdown_list
    )
