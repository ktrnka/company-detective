import reddit.summarizer
import reddit.search
import reddit.fetch

from core import CompanyProduct
from search import SearchResult

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class RedditSummary:
    sources: List[SearchResult]
    threads: List[reddit.fetch.Submission]
    summary: reddit.summarizer.SummaryResult


def run(
    target: CompanyProduct, num_threads: int = 2, min_comments: int = 2
) -> Optional[RedditSummary]:
    reddit_client = reddit.fetch.init()

    # Search for URLs
    search_results = reddit.search.find_submissions(target, num_results=num_threads)

    # Fetch the Submissions from Reddit
    post_submissions = [
        reddit_client.submission(url=result.link) for result in search_results
    ]

    # Filter Submissions to only those with enough comments
    post_submissions = [
        submission
        for submission in post_submissions
        if submission.num_comments >= min_comments
    ]

    if len(post_submissions) == 0:
        print(f"No posts with enough comments found for {target}")
        return None

    # Limit the number of threads
    post_submissions = post_submissions[:num_threads]

    # Aggregate the summaries
    result = reddit.summarizer.summarize(target, post_submissions)

    return RedditSummary(
        sources=search_results, threads=post_submissions, summary=result
    )
