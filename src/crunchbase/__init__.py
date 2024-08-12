from search import search
from core import CompanyProduct

from .models import *

def find_people_url(target: CompanyProduct) -> str:
    """Find the Crunchbase people page for a company using Google search"""
    result = next(search(f'site:www.crunchbase.com/organization "{target.company}"', num=1))
    assert "/organization/" in result.link

    return f"{result.link}/people"

