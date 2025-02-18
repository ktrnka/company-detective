from functools import lru_cache
from typing import List

from core import Seed
from utils.google_search import search, SearchResult


@lru_cache(1000)
def find_news_articles(
    target: Seed, num_results=10, date_restrict="y1"
) -> List[SearchResult]:
    query = f'"{target.company}" related:{target.domain}'
    if target.product != target.company:
        query += f' "{target.product}"'
    query += " news -site:reddit.com -site:twitter.com -site:x.com -site:linkedin.com"

    return list(
        result for result in search(query, num=num_results, dateRestrict=date_restrict, drop_duplicates=True)
    )
