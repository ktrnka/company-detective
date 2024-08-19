from typing import NamedTuple, Set
import re
import os
from datetime import datetime, timedelta
from langchain.globals import set_llm_cache
from langchain.cache import SQLiteCache
import requests_cache

import re
import urllib.parse
from loguru import logger


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
        cache_path,
        backend="sqlite",
        expire_after=timedelta(days=7),
        allowable_codes=[200, 403],
    )

    # I originally tried cache_control=True but many news sites disable caching entirely which isn't what I want during development

    # TODO: There's a design limitation in how this interacts with throttling, like in the news article scraper. Though the news article scraper also does a lru in-memory cache, so it only matters on fresh notebooks.

    return cache_path


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


def simplify_markdown(markdown_doc: str) -> str:
    # TODO: Improve this, write tests, etc
    return markdown_doc.strip().strip("```markdown").strip("```")


def extract_core_domain(url: str) -> str:
    """Extract the core part of a domain, e.g. 'reddit' from 'https://www.reddit.com/r/freelance/comments/p2cdrt/gunio_rejected_me_immediately/'"""
    domain = urllib.parse.urlparse(url).hostname
    domain_parts = domain.split(".")
    if domain_parts[-1] in {"com", "net", "org"}:
        domain_parts = domain_parts[:-1]
    if domain_parts[0] == "www":
        domain_parts = domain_parts[1:]
    return ".".join(domain_parts)


def test_extract_core_domain():
    assert (
        extract_core_domain(
            "https://www.reddit.com/r/freelance/comments/p2cdrt/gunio_rejected_me_immediately/"
        )
        == "reddit"
    )
    assert (
        extract_core_domain(
            "https://www.glassdoor.com/Reviews/Employee-Review-Gun-io-RVW34284332.htm"
        )
        == "glassdoor"
    )
    assert (
        extract_core_domain(
            "https://gun.io/guest-posts/2023/09/junior-sql-developer-job-description/"
        )
        == "gun.io"
    )
    assert extract_core_domain("https://bit.ly/3P9HRMV") == "bit.ly"
    assert extract_core_domain("http://test") == "test"


class URLShortener:
    """
    Shorten URLs in markdown to a cache URL with functionality to unshorten them.
    This is designed to reduce the number of tokens in the LLM input and output, which can improve speed and reduce cost.
    It also tends to increase the overall output length.
    """

    def __init__(self):
        self.url_cache = {}
        self.counter = 0

    def shorten_markdown(self, markdown: str) -> str:
        def replace_url(match):
            url = match.group(0)
            if url not in self.url_cache:
                self.counter += 1
                domain = extract_core_domain(url)

                self.url_cache[url] = f"cache://{domain}/{self.counter}"
            return self.url_cache[url]

        shortened_markdown = re.sub(r"(https?://[^\s)]+)", replace_url, markdown)

        logger.info(
            f"{len(markdown):,} -> {len(shortened_markdown):,} chars ({len(shortened_markdown) / len(markdown):.0%} of original)"
        )

        return shortened_markdown

    def unshorten_markdown(self, markdown: str) -> str:
        def replace_short_url(match):
            short_url = match.group(0)
            for url, shortened in self.url_cache.items():
                if shortened == short_url:
                    return url
            return short_url

        unshortened_markdown = re.sub(r"cache://[^\s)]+", replace_short_url, markdown)
        logger.info(
            f"{len(markdown):,} -> {len(unshortened_markdown):,} chars ({len(unshortened_markdown) / len(markdown):.0%} of original)"
        )

        return unshortened_markdown


def test_url_shortener():
    example_md = """
# Bibliography

### Reddit
- [DeeRegs, Reddit, 2021-08-11](https://www.reddit.com/r/freelance/comments/p2cdrt/gunio_rejected_me_immediately/)
- [LeyKlussyn, Reddit, 2021-08-11](https://www.reddit.com/r/freelance/comments/p2cdrt/gunio_rejected_me_immediately/h8lbqse/)
- [dustinechos, Reddit, 2021-08-12](https://www.reddit.com/r/freelance/comments/p2cdrt/gunio_rejected_me_immediately/h8lwjj6/)
- [ork4n, Reddit, 2021-09-02](https://www.reddit.com/r/freelance/comments/p2cdrt/gunio_rejected_me_immediately/hb9vnff/)
- [solid_steel, Reddit, 2016-08-13](https://www.reddit.com/r/freelance/comments/4xibr5/do_sites_like_toptal_staffzen_gunio_crew/d6fqpy5/)
- [cclites, Reddit, 2016-08-13](https://www.reddit.com/r/freelance/comments/4xibr5/do_sites_like_toptal_staffzen_gunio_crew/d6ft7g1/)
- [pdevito3, Reddit, 2022-04-29](https://www.reddit.com/r/freelance/comments/uelpju/gunio_users_you_might_need_an_extra_active_step/)
- [markcloud23, Reddit, 2024-03-25](https://www.reddit.com/r/webdev/comments/10kdu6f/best_toptal_alternatives_for_finding_high_paying/kwh10c0/)
- [wehivo9, Reddit, 2023-01-24](https://www.reddit.com/r/webdev/comments/10kdu6f/best_toptal_alternatives_for_finding_high_paying/)
- [League-Ill, Reddit, 2023-09-07](https://www.reddit.com/r/startups/comments/16cck2y/gripe_about_developer_talent_on_upwork/jzlem6l/)
- [Beginning-Comedian-2, Reddit, 2024-06-10](https://www.reddit.com/r/reactjs/comments/xrwxr6/best_place_to_hire_quality_react_developers_for/l80by6f/)
- [FlexJobs, Reddit, 2018-06-20](https://www.reddit.com/r/digitalnomad/comments/8sbpho/remote_part_time_work_while_i_live_in_south/e10awdc/)

### Glassdoor
- [Associate, Glassdoor, 2020-07-17](https://www.glassdoor.com/Reviews/Employee-Review-Gun-io-RVW34284332.htm)
- [Client Growth Associate, Glassdoor, 2021-02-11](https://www.glassdoor.com/Reviews/Employee-Review-Gun-io-RVW42349229.htm)
- [Anonymous, Glassdoor, 2021-02-26](https://www.glassdoor.com/Reviews/Employee-Review-Gun-io-RVW43161322.htm)
- [Anonymous, Glassdoor, 2021-11-03](https://www.glassdoor.com/Reviews/Employee-Review-Gun-io-RVW54871286.htm)
- [Presales Solutions Architect, Glassdoor, 2022-01-31](https://www.glassdoor.com/Reviews/Employee-Review-Gun-io-RVW58860158.htm)
- [Account Manager, Glassdoor, 2021-03-30](https://www.glassdoor.com/Reviews/Employee-Review-Gun-io-RVW44794895.htm)
- [Account Executive, Glassdoor, 2021-05-03](https://www.glassdoor.com/Reviews/Employee-Review-Gun-io-RVW46389131.htm)
- [Software Engineer, Glassdoor, 2023-12-28](https://www.glassdoor.com/Reviews/Employee-Review-Gun-io-RVW82904632.htm)
- [Marketing, Glassdoor, 2024-02-23](https://www.glassdoor.com/Reviews/Employee-Review-Gun-io-RVW84685389.htm)

### News
- [Scott Stockdale, Gun.io, September 2023](https://gun.io/guest-posts/2023/09/junior-sql-developer-job-description/)
- [Victoria Stahr, Gun.io, July 2024](https://gun.io/news/2024/07/how-to-get-involved-with-the-gun-io-community/)
- [Chris Johnson, Gun.io, May 2024](https://gun.io/news/2024/05/gunai-revolutionize-tech-hiring/)
- [Greater Nashville Tech Council, 2022-08-09](https://bit.ly/3P9HRMV)
- [Vicky, Twine, April 2024](https://www.twine.net/blog/the-10-best-alternatives-to-toptal/)
"""

    url_shortener = URLShortener()
    shortened_md = url_shortener.shorten_markdown(example_md)
    print(shortened_md)

    assert example_md == url_shortener.unshorten_markdown(shortened_md)


from typing import Iterable, Hashable, List


def iterate_ngrams(tokens: List[Hashable], n: int) -> Iterable[tuple]:
    for i in range(len(tokens) - n + 1):
        yield tuple(tokens[i : i + n])


def test_iterate_ngrams():
    assert list(iterate_ngrams(["a", "b", "c", "d"], 2)) == [
        ("a", "b"),
        ("b", "c"),
        ("c", "d"),
    ]


def tokenize(text: str) -> List[str]:
    # NOTE: This is a very, very basic tokenizer for very basic tasks.
    return re.split(r"\W+", text)


def test_tokenize():
    assert tokenize("a b c") == ["a", "b", "c"]
    assert tokenize("a, b, c") == ["a", "b", "c"]


def extractive_fraction(summary: str, source: str, n: int = 4):
    summary_ngrams = set(iterate_ngrams(tokenize(summary), n))
    source_ngrams = set(iterate_ngrams(tokenize(source), n))
    return len(summary_ngrams & source_ngrams) / len(summary_ngrams)


def test_extractive_fraction():
    example_source = "a b c d e f g h i j k l m n o p q r s t u v w x y z"
    example_summary = "a b c d e f g h i j k"

    assert extractive_fraction(example_summary, example_source) == 1.0

    example_source = "a b c d e f g h i j k l m n o p q r s t u v w x y z"
    example_summary = "a b c d e g h i j k"

    assert extractive_fraction(example_summary, example_source) < 1.0


def extract_urls(markdown: str) -> List[str]:
    return re.findall(r"\[[^]]+\]\(([^)\]]+)\)", markdown)


def test_extract_urls():
    assert extract_urls("[a](b) [c](d)") == ["b", "d"]

    # Sometimes the LLM mangles the Markdown and we ignore those
    assert extract_urls("[a](b) [c](d [e](f)") == ["b", "f"]


def extractive_fraction_urls(summary: str, source: str) -> float:
    summary_urls = set(extract_urls(summary))
    source_urls = set(extract_urls(source))
    return len(summary_urls & source_urls) / len(summary_urls)


def extract_suspicious_urls(summary: str, source: str) -> Set[str]:
    summary_urls = set(extract_urls(summary))
    source_urls = set(extract_urls(source))

    return summary_urls.difference(source_urls)


def test_extractive_fraction_urls():
    example_source = "[a](b) [c](d) [e](f) [g](h)"
    example_summary = "[a](b) [c](d) [e](f)"

    assert extractive_fraction_urls(example_summary, example_source) == 1.0

    example_summary = "[a](b) [c](d) [e](l)"
    assert extractive_fraction_urls(example_summary, example_source) == 2 / 3


def num_cache_mentions(llm_output: str) -> int:
    """Count the number of cache:// in the output. It should be zero."""
    mentions = re.findall(r"\bcache://", llm_output, re.IGNORECASE)
    return len(mentions)


def test_num_cache_mentions():
    assert num_cache_mentions("cache://1") == 1
    assert num_cache_mentions("cache://234 [hi](cache://567)") == 2
