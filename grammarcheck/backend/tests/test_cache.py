from services.cache_service import CacheService


def test_cache_set_and_get():
    cache = CacheService()
    cache.set("hello", "gemma4", {"corrected": "world"})
    result = cache.get("hello", "gemma4")
    assert result == {"corrected": "world"}


def test_cache_miss():
    cache = CacheService()
    result = cache.get("nonexistent", "gemma4")
    assert result is None


def test_cache_different_model():
    cache = CacheService()
    cache.set("hello", "gemma4", {"corrected": "world"})
    result = cache.get("hello", "gemma3")
    assert result is None


def test_cache_clear():
    cache = CacheService()
    cache.set("a", "gemma4", {"v": 1})
    cache.set("b", "gemma4", {"v": 2})
    assert cache.size == 2
    cache.clear()
    assert cache.size == 0


def test_cache_eviction():
    cache = CacheService()
    cache._max_size = 2
    cache.set("a", "gemma4", {"v": 1})
    cache.set("b", "gemma4", {"v": 2})
    cache.set("c", "gemma4", {"v": 3})
    assert cache.size == 2
    assert cache.get("a", "gemma4") is None
    assert cache.get("b", "gemma4") is not None
    assert cache.get("c", "gemma4") is not None
