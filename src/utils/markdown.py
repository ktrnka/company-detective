import re

CACHE_LINK_PATTERN = re.compile(r"\[([^\]]+)\]\(cache://([^\)]+)\)")

def strip_cache_links(markdown: str) -> str:
    return CACHE_LINK_PATTERN.sub(r"\1", markdown)

def test_strip_cache_links():
    assert strip_cache_links("") == ""

    # Don't strip normal links
    assert strip_cache_links("cache://example.com") == "cache://example.com"

    # Don't strip non-cache MD links
    assert strip_cache_links("[example](http://example.com)") == "[example](http://example.com)"

    # Strip cache MD links
    assert strip_cache_links("[example](cache://example.com)") == "example"

    # Strip it even if it's in citation format
    assert strip_cache_links("[(example, 2019)](cache://example.com)") == "(example, 2019)"
