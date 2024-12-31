from datetime import timedelta
from typing import List, Optional
import diskcache
import tempfile


class CollectionCache:
    """
    Wrapper around a traditional cache that builds up the collection.

    Key assumptions:
    - Each item has an ID
    - Each item has a date
    - There's an underlying storage layer that this class doesn't implement
    """

    def __init__(self, cache: diskcache.Cache, ttl: timedelta):
        self.cache = cache
        self.ttl = ttl

    def upsert_dict(self, key: str, items: dict):
        """
        Upsert a collection of items into the cache.

        The items dict should be a mapping of ID to items, which are typically nested dicts
        """
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
        return self.cache.get(key, None)

    def get_list(self, key: str) -> Optional[list]:
        """
        Get the collection of items for a given key.
        """
        item_map = self.get_dict(key)
        if not item_map:
            return None
        return list(item_map.values())


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
