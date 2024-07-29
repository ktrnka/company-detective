import praw
from dotenv import load_dotenv
import os
from datetime import datetime
from praw.models import MoreComments, Submission, Comment
from googlesearch import search
from functools import lru_cache
from typing import Iterable
import re

from core import CompanyProduct


def init() -> praw.Reddit:
    load_dotenv()

    return praw.Reddit(
        client_id=os.environ["REDDIT_CLIENT_ID"],
        client_secret=os.environ["REDDIT_CLIENT_SECRET"],
        user_agent="Comment Extraction (by u/trnka)",
    )


DATE_FORMAT = "%Y-%m-%d"


def utc_to_date(utc: float):
    return datetime.utcfromtimestamp(utc).strftime(DATE_FORMAT)


def include_comment(comment: Comment):
    """Decide whether to include a comment in the output"""
    return (
        not isinstance(comment, MoreComments)
        and not comment.stickied
        and comment.score > 0
    )


def comment_forest_to_markdown(comment: Comment, level=1, parent_id=None, max_depth=4):
    """
    Recursively format a Reddit comment tree into a markdown-like text with basic filtering and depth control.
    """
    if not include_comment(comment) or level > max_depth:
        return ""

    parent_header = f" (in reply to {parent_id})" if parent_id else ""
    text = f"{'#' * level} Comment ID {comment.id} by {comment.author} on {utc_to_date(comment.created_utc)} [{comment.score:+d} votes]{parent_header}:\n"
    text += f"{comment.body}\n\n"

    text += "\n\n".join(
        comment_forest_to_markdown(reply, level + 1, parent_id=comment.id)
        for reply in comment.replies
    )

    return text


def submission_to_markdown(submission: Submission, pagination_limit=10) -> str:
    """
    Format a Reddit thread into a markdown-like text with basic filtering and depth control.
    """
    submission.comments.replace_more(limit=pagination_limit)

    text = f"""
# Post ID {submission.id}:  {submission.title} by {submission.author} on {utc_to_date(submission.created_utc)} [{submission.score:+d} votes]
{submission.selftext}

"""

    text += "\n\n".join(
        comment_forest_to_markdown(reply, 2, parent_id=submission.id)
        for reply in submission.comments
    )
    return text


def test_submission():
    """Test that we can connect to Reddit, pull a thread, and format it"""
    reddit_client = init()

    submission = reddit_client.submission(
        url="https://www.reddit.com/r/ChatGPT/comments/11twe7z/prompt_to_summarize/"
    )
    print(submission_to_markdown(submission))


REDDIT_COMMENTS_URL_PATTERN = re.compile(r".*/comments/.+")


@lru_cache(1000)
def find_submission_urls(
    target: CompanyProduct, results_per_page=10, num_results=10, pause_seconds=2
) -> Iterable[str]:
    query = f'site:reddit.com "{target.company}""'
    if target.product != target.company:
        query += f' "{target.product}"'

    return list(
        url
        for url in search(
            query, num=results_per_page, stop=num_results, pause=pause_seconds
        )
        if REDDIT_COMMENTS_URL_PATTERN.match(url)
    )

def index_comment_forest_permalinks(comment: Comment, depth_remaining=3) -> dict:
    """
    Index all the permalinks in a Reddit comment tree.
    """
    if depth_remaining <= 0 or not include_comment(comment):
        return {}

    permalinks = {}
    for reply in comment.replies:
        permalinks.update(index_comment_forest_permalinks(reply, depth_remaining - 1))
    permalinks[comment.id] = comment.permalink
    return permalinks

def index_permalinks(submission: Submission) -> dict:
    """
    Index all the permalinks in a Reddit submission.
    """
    permalinks = {}
    for comment in submission.comments.list():
        if include_comment(comment):
            permalinks.update(index_comment_forest_permalinks(comment))
    permalinks[submission.id] = submission.permalink
    return permalinks



def test_search():
    """Test that we can issue a Google search against Reddit and get some results"""
    for url in find_submission_urls(CompanyProduct("Singularity 6", "Palia"), num_results=20):
        print(url)
