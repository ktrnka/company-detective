import asyncpraw
from dotenv import load_dotenv
import os
from datetime import datetime
from asyncpraw.models import MoreComments, Submission, Comment
import pytest


DATE_FORMAT = "%Y-%m-%d"


def utc_to_date(utc: float):
    return datetime.utcfromtimestamp(utc).strftime(DATE_FORMAT)


def init() -> asyncpraw.Reddit:
    load_dotenv()

    return asyncpraw.Reddit(
        client_id=os.environ["REDDIT_CLIENT_ID"],
        client_secret=os.environ["REDDIT_CLIENT_SECRET"],
        user_agent="Comment Extraction (by u/trnka)",
    )


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

    optional_parent_header = f" (in reply to ID {parent_id})" if parent_id else ""
    text = f"{'#' * level} Comment ID {comment.id} with {comment.score:+d} score by [({comment.author}, Reddit, {utc_to_date(comment.created_utc)})](https://www.reddit.com{comment.permalink}){optional_parent_header}:\n"
    text += f"{comment.body.strip()}\n\n"

    text += "\n\n".join(
        comment_forest_to_markdown(reply, level + 1, parent_id=comment.id)
        for reply in comment.replies
    )

    return text.strip()


async def submission_to_markdown(submission: Submission, pagination_limit=10) -> str:
    """
    Format a Reddit thread into a markdown-like text with permalinks, basic filtering, and depth control.
    """
    await submission.comments.replace_more(limit=pagination_limit)

    text = f"""
# Post ID {submission.id}: {submission.title} with {submission.score:+d} score by [({submission.author}, Reddit, {utc_to_date(submission.created_utc)})](https://www.reddit.com{submission.permalink})
{submission.selftext}

"""

    text += "\n\n".join(
        comment_forest_to_markdown(reply, 2, parent_id=submission.id)
        for reply in submission.comments
    )
    return text.strip()


@pytest.mark.skip(reason="Uses network and API key")
def test_submission():
    """Test that we can connect to Reddit, pull a thread, and format it"""
    reddit_client = init()

    submission = reddit_client.submission(
        url="https://www.reddit.com/r/ChatGPT/comments/11twe7z/prompt_to_summarize/"
    )
    print(submission_to_markdown(submission))
