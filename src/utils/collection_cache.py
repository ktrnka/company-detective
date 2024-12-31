from collections.abc import Container
from datetime import datetime, timedelta
from typing import List, Optional
import diskcache
import tempfile


class CollectionCache(Container):
    """
    Wrapper around a diskcache.Cache that builds up a collection of items with IDs. This is meant for situations like
    caching reviews from review sites in which we want to merge subsequent crawls of those reviews.

    Key assumptions:
    - Each item has an ID
    - Each item has a date
    - There's an underlying storage layer that this class doesn't implement
    """

    def __init__(self, cache: diskcache.Cache, ttl: timedelta, key_prefix: str = "collection_cache:"):
        self.cache = cache
        self.ttl = ttl
        self.key_prefix = key_prefix

    def _key(self, key: str) -> str:
        return f"{self.key_prefix}{key}" if self.key_prefix else key

    def upsert_dict(self, key: str, items: dict):
        """
        Upsert a collection of items into the cache.

        The items dict should be a mapping of ID to items, which are typically nested dicts
        """
        key = self._key(key)

        if key in self.cache:
            existing = self.cache[key]
            existing.update(items)
            self.cache.set(key, existing, expire=self.ttl.total_seconds())
        else:
            self.cache.set(key, items, expire=self.ttl.total_seconds())

    def upsert_list(self, key: str, id_field: str, items: List[dict]):
        """
        Upsert a collection of items into the cache.

        The items list should be a list of items, which are typically nested dicts. This is a convenience method for creating an ID-indexed dict and calling upsert.
        """
        self.upsert_dict(key, {item[id_field]: item for item in items})

    def get_dict(self, key: str) -> Optional[dict]:
        """
        Get the collection of items for a given key.
        """
        key = self._key(key)
        return self.cache.get(key, None)

    def get_list(self, key: str) -> Optional[list]:
        """
        Get the collection of items for a given key.
        """
        item_map = self.get_dict(key)
        if not item_map:
            return None
        return list(item_map.values())
    
    def __contains__(self, key: str) -> bool:
        return self._key(key) in self.cache
    
    def get_expiry(self, key: str) -> Optional[datetime]:
        """
        Get the expiry time for a key.
        """
        _, expiry_seconds = self.cache.get(self._key(key), expire_time=True)
        if not expiry_seconds:
            return None
        return datetime.fromtimestamp(expiry_seconds)
    
    def get_remaining_ttl(self, key: str) -> Optional[timedelta]:
        expiry = self.get_expiry(key)
        if not expiry:
            return None
        return expiry - datetime.now()
    
    def get_age(self, key: str) -> Optional[timedelta]:
        """Get the age of this key in the cache, assuming it was stored with the same TTL as this cache"""
        remaining_ttl = self.get_remaining_ttl(key)
        if not remaining_ttl:
            return None
        return self.ttl - remaining_ttl
    

def test_collection_cache_upsert():
    with tempfile.TemporaryDirectory() as temp_dir:
        cache = diskcache.Cache(temp_dir)
        collection_cache = CollectionCache(cache, ttl=timedelta(minutes=5))

        key = "test-key"

        collection_cache.upsert_list(
            key,
            "id",
            [
                {"id": 1, "name": "item1"},
                {"id": 2, "name": "item2"},
            ],
        )

        cached_dict = collection_cache.get_dict(key)

        assert len(cached_dict) == 2
        assert cached_dict[1]["name"] == "item1"
        assert cached_dict[2]["name"] == "item2"

        collection_cache.upsert_list(
            key,
            "id",
            [
                {"id": 2, "name": "updated_item2"},
                {"id": 3, "name": "item3"},
            ],
        )

        cached_dict = collection_cache.get_dict(key)

        assert len(cached_dict) == 3
        assert cached_dict[1]["name"] == "item1"
        assert cached_dict[2]["name"] == "updated_item2"
        assert cached_dict[3]["name"] == "item3"

        # test contains
        assert key in collection_cache
        assert "1235" not in collection_cache

        # test expiry
        expiry = collection_cache.get_expiry(key)
        assert expiry > datetime.now()

        assert collection_cache.get_expiry("1235") is None