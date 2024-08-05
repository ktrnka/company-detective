from functools import lru_cache
from typing import List

from core import CompanyProduct
from search import search, SearchResult


@lru_cache(1000)
def find_news_articles(
    target: CompanyProduct, num_results=10, date_restrict="y1"
) -> List[SearchResult]:
    query = f'"{target.company}"'
    if target.product != target.company:
        query += f' "{target.product}"'
    query += " news"

    return list(
        result for result in search(query, num=num_results, dateRestrict=date_restrict)
    )
