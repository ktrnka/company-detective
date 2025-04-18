import sys
from typing import NamedTuple, Optional, Set, List, Tuple, Iterable
import re
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from langchain.globals import set_llm_cache
from langchain_community.cache import SQLiteCache
from pydantic import BaseModel
import requests_cache
import diskcache

import re
import urllib.parse
from loguru import logger

from utils.markdown_utils import extract_urls

class Product(NamedTuple):
    name: str

    webpage_url: Optional[str] = None
    steam_url: Optional[str] = None
    google_play_url: Optional[str] = None
    apple_app_store_url: Optional[str] = None

class FeatureFlags(NamedTuple):
    require_news_backlinks: bool = False
    require_reddit_backlinks: bool = False

class Seed(NamedTuple):
    # TODO: Naming
    company: str

    # The old product field, replaced with a property
    deprecated_product: str

    domain: str

    keywords: Optional[Set[str]] = None

    # These aren't used anymore, but if we want to load the old result files, we need to keep them around
    # I'd start them with an underscore but NamedTuple doesn't allow that
    deprecated_require_news_backlinks: bool = False
    deprecated_require_reddit_backlinks: bool = False

    # New style: Something like this will replace product: str.
    primary_product: Optional[Product] = None

    # New style of feature flags
    feature_flags: Optional[FeatureFlags] = None

    @property
    def product(self) -> str:
        if self.primary_product:
            return self.primary_product.name
        
        # Keeping this around just in case of old loaded data
        if self.deprecated_product:
            return self.deprecated_product
        
        # Fall back to the company name
        return self.company
    
    @classmethod
    def init(cls, company: str, domain: str, product: Optional[str] = None, keywords: Optional[Iterable[str]] = None, primary_product: Optional[Product] = None, feature_flags: Optional[FeatureFlags] = None) -> "Seed":
        """Helper to initialize with optional fields"""
        if not product:
            product = company
        return cls(company, product, domain, frozenset(keywords) if keywords else None, feature_flags.require_news_backlinks, feature_flags.require_reddit_backlinks, primary_product, feature_flags)
    
    def as_path_v2(self) -> str:
        if self.company == self.product:
            unescaped = self.company
        else:
            unescaped = f"{self.company} {self.product}"

        return re.sub(r"[^a-zA-Z0-9]", "_", unescaped)
    
class SeedValidator(BaseModel):
    value: Seed

    @classmethod
    def validate(cls, seed: Seed):
        return cls(value=seed)

def get_project_dir(relative_path: str, create_if_needed=True) -> str:
    """Get the path of a file from the project root"""
    current_file = os.path.abspath(__file__)
    project_root = os.path.dirname(os.path.dirname(current_file))
    project_dir = os.path.join(project_root, relative_path)

    if create_if_needed:
        os.makedirs(project_dir, exist_ok=True)

    return project_dir


def make_experiment_dir(target: Seed) -> str:
    """
    Create a directory for the output of an experiment and return it, based on the company and product names. It's meant to provide some consistency for experimentation.
    """
    folder_name = re.sub(r"[^a-zA-Z0-9]", "_", f"{target.company} {target.product}")
    timestamp = datetime.now().strftime("%Y-%m-%d")

    folder_path = f"output/{folder_name}/{timestamp}"

    return get_project_dir(folder_path)


def eval_filename(target: Seed, extension="html") -> str:
    folder_path = get_project_dir(f"output/{target.as_path_v2()}")

    # Create the filename using the current timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{folder_path}/{target.as_path_v2()}_{timestamp}.{extension}"

    return filename


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
        urls_expire_after = {
            # Don't cache Airtable API requests
            'api.airtable.com': requests_cache.DO_NOT_CACHE,
        },
        allowable_codes=[200, 403],
    )

    # I originally tried cache_control=True but many news sites disable caching entirely which isn't what I want during development

    # TODO: There's a design limitation in how this interacts with throttling, like in the news article scraper. Though the news article scraper also does a lru in-memory cache, so it only matters on fresh notebooks.

    return cache_path


def init(loguru_level="INFO"):
    """
    Initialize for regular development: load the .env file, initialize the langchain cache, initialize the requests cache, and initialize the logging level
    """
    load_dotenv()
    init_langchain_cache()
    init_requests_cache()

    logger.remove()
    logger.add(sys.stderr, level=loguru_level)


def extract_core_domain(url: str) -> str:
    """Extract the core part of a domain, e.g. 'reddit' from 'https://www.reddit.com/r/freelance/comments/p2cdrt/gunio_rejected_me_immediately/'"""

    try:
        domain = urllib.parse.urlparse(url).hostname
        domain_parts = domain.split(".")
        if domain_parts[-1] in {"com", "net", "org"}:
            domain_parts = domain_parts[:-1]
        if domain_parts[0] == "www":
            domain_parts = domain_parts[1:]
        return ".".join(domain_parts)
    except:
        logger.warning(f"Failed to extract core domain from: {url}, defaulting to misc")
        return "misc"


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

def repair_links(markdown: str) -> str:
    """Repair links in the markdown that aren't proper markdown due to the LLM"""
    return re.sub(r"\(([^)\]]+)]", r"(\1)", markdown)

def test_repair_links():
    # The most common situation is that the closing paren becomes a bracket
    assert repair_links("[a](b) [c](d] [e](f)") == "[a](b) [c](d) [e](f)"

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
        # Prevent logger crash on empty string
        if not markdown:
            return markdown

        def replace_url(match):
            url = match.group(0)
            if url not in self.url_cache:
                self.counter += 1
                domain = extract_core_domain(url)

                self.url_cache[url] = f"cache://{domain}/{self.counter}"
            return self.url_cache[url]

        shortened_markdown = re.sub(r"(https?://[^\s)\]]+)", replace_url, markdown)

        logger.debug(
            f"{len(markdown):,} -> {len(shortened_markdown):,} chars ({len(shortened_markdown) / len(markdown):.0%} of original)"
        )

        return shortened_markdown

    def unshorten_markdown(self, markdown: str) -> str:
        # Prevent logger crash on empty string
        if not markdown:
            return markdown

        def replace_short_url(match):
            short_url = match.group(0)
            for url, shortened in self.url_cache.items():
                if shortened == short_url:
                    return url
            return short_url

        unshortened_markdown = re.sub(r"cache://[^\s)\]]+", replace_short_url, markdown)
        logger.debug(
            f"{len(markdown):,} -> {len(unshortened_markdown):,} chars ({len(unshortened_markdown) / len(markdown):.0%} of original)"
        )

        return unshortened_markdown


def test_url_shortener():
    example = """
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
    shortened = url_shortener.shorten_markdown(example)
    print(shortened)

    assert len(shortened) < len(example)
    assert example == url_shortener.unshorten_markdown(shortened)

    example = """
- ([Marketing, Glassdoor, 2024-02-24](https://www.glassdoor.com/Reviews/Employee-Review-Gun-io-RVW84685389.htm))
- [(Marketing, Glassdoor, 2024-02-25)](https://www.glassdoor.com/Reviews/Employee-Review-Gun-io-RVW84685389.htm)
- [https://www.glassdoor.com/](https://www.glassdoor.com/)
"""

    shortened = url_shortener.shorten_markdown(example)
    print(shortened)
    assert len(shortened) < len(example)
    assert example == url_shortener.unshorten_markdown(shortened)

    example = """[https://www.aainsure.net](https://www.aainsure.net)"""
    shortened = url_shortener.shorten_markdown(example)

    # test that it works
    assert len(shortened) < len(example)
    assert example == url_shortener.unshorten_markdown(shortened)

    # NOTE: Originally I wanted it to only shorten the link part, but it's fine if it shortens both, separately
    # test that it works the way I want it to
    # assert shortened.startswith("[https://www.aainsure.net](cache://aainsure/")


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


def extractive_fraction_urls(summary: str, source: str) -> float:
    summary_urls = set(extract_urls(summary))
    source_urls = set(extract_urls(source))
    return len(summary_urls & source_urls) / len(summary_urls)


def extract_suspicious_urls(summary: str, source: str) -> Set[str]:
    summary_urls = set(extract_urls(summary))
    source_urls = set(extract_urls(source))

    suspicious_urls = summary_urls.difference(source_urls)

    # Secondary filter: This handles situations where the URL is in the summary text but not in the set of URLs extracted from the source. This could be due to the URL being slightly altered by the LLM.
    # Iterate over a copy of the set so that we can modify it
    for url in list(suspicious_urls):
        if url in source:
            suspicious_urls.remove(url)

    return suspicious_urls


def citation_density(summary: str) -> float:
    summary_urls = extract_urls(summary)

    num_link_syntax_chars = 4
    return sum(len(url) + num_link_syntax_chars for url in summary_urls) / len(summary)


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


def log_summary_metrics(summary: str, summary_input: str, extractive=True):
    # Get a logger for higher up the call stack so that the log messages are associated with the right function
    caller_logger = logger.opt(depth=1)

    good_icon = "✅"
    neutral_icon = ""
    bad_icon = "❌"

    if not summary:
        caller_logger.warning("No summary")
        return
    
    if not summary_input:
        caller_logger.warning("No summary input")
        return

    caller_logger.info(
        "{:,} -> {:,} chars ({:.0%}) {}",
        len(summary_input),
        len(summary),
        len(summary) / len(summary_input),
        neutral_icon if len(summary) / len(summary_input) < 1 else neutral_icon,
    )

    # Smoke tests
    try:
        stat_extractive_fraction = extractive_fraction(summary, summary_input)
        quality_threshold = 0.4 if extractive else 0.05
        caller_logger.info(
            "Extractive fraction: {:.0%} {}",
            stat_extractive_fraction,
            neutral_icon if stat_extractive_fraction > quality_threshold else bad_icon,
        )
    except ZeroDivisionError:
        caller_logger.info("Extractive fraction: Summary is too short for ngrams")

    try:
        stat_extractive_fraction_urls = extractive_fraction_urls(summary, summary_input)
        caller_logger.info(
            "Percent of URLs in sources: {:.0%} {}",
            stat_extractive_fraction_urls,
            good_icon if stat_extractive_fraction_urls == 1.0 else bad_icon,
        )
    except ZeroDivisionError:
        caller_logger.info("Percent of URLs in sources: No URLs in summary")

    stat_citation_density = citation_density(summary)
    caller_logger.info(
        "Citation density: {:.1%} (percent of output used by URLs/link syntax) {}",
        stat_citation_density,
        neutral_icon if stat_citation_density > 0.05 else bad_icon,
    )

    caller_logger.info("Distinct URLs (summary / input): {} / {}", len(set(extract_urls(summary))), len(set(extract_urls(summary_input))))

    caller_logger.info(
        "Suspicious URLs: {}", extract_suspicious_urls(summary, summary_input)
    )

    cache_mentions = num_cache_mentions(summary)
    caller_logger.info(
        "Cache mentions: {} {}",
        cache_mentions,
        good_icon if cache_mentions == 0 else bad_icon,
    )


def test_log_summary_metrics():
    log_summary_metrics("a b c", "a b c")
    log_summary_metrics("a b c", "a b d")
    log_summary_metrics("a b c", "a b c d")
    log_summary_metrics("a b c", "a b c d e f g h i j k l m n o p q r s t u v w x y z")

def log_map_reduce_metrics(input_documents: List[str], intermediate_steps: List[str], output_text: str):
    """Log the metrics for a map-reduce summarization process"""
    caller_logger = logger.opt(depth=1)

    input_length = sum(len(doc) for doc in input_documents)
    intermediate_length = sum(len(text) for text in intermediate_steps)
    summary_length = len(output_text)

    caller_logger.info(
        "Map stage {:,} chars -> {:,} chars ({:.0%})",
        input_length,
        intermediate_length,
        intermediate_length / input_length,
    )

    caller_logger.info(
        "Reduce stage {:,} chars -> {:,} chars ({:.0%})",
        intermediate_length,
        summary_length,
        summary_length / intermediate_length if intermediate_length > 0 else -1,
    )

# Things to run ONCE
cache = diskcache.Cache(directory=get_project_dir(".cache/diskcache"))
