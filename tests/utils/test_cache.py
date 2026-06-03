from utils.cache import RedisCache, TTLMemoryCache


def test_ttl_memory_cache_returns_value_before_expiration(monkeypatch):
    clock = [1000]
    monkeypatch.setattr("utils.cache.time.time", lambda: clock[0])
    cache = TTLMemoryCache()

    cache.set("login:user:ana@example.com", {"id": "user-1"}, ttl_seconds=10)

    assert cache.get("login:user:ana@example.com") == {"id": "user-1"}


def test_ttl_memory_cache_removes_expired_value(monkeypatch):
    clock = [1000]
    monkeypatch.setattr("utils.cache.time.time", lambda: clock[0])
    cache = TTLMemoryCache()

    cache.set("login:user:ana@example.com", {"id": "user-1"}, ttl_seconds=10)
    clock[0] = 1011

    assert cache.get("login:user:ana@example.com") is None


def test_ttl_memory_cache_deletes_value():
    cache = TTLMemoryCache()
    cache.set("login:user:ana@example.com", {"id": "user-1"}, ttl_seconds=10)

    cache.delete("login:user:ana@example.com")

    assert cache.get("login:user:ana@example.com") is None


def test_redis_cache_reads_json_from_client():
    client = MockRedisClient()
    client.values["login:user:ana@example.com"] = '{"id": "user-1"}'
    cache = RedisCache("rediss://example.com")
    cache._client = client

    assert cache.get("login:user:ana@example.com") == {"id": "user-1"}


def test_redis_cache_writes_with_ttl_and_keeps_memory_fallback():
    client = MockRedisClient()
    cache = RedisCache("rediss://example.com")
    cache._client = client

    cache.set("login:user:ana@example.com", {"id": "user-1"}, ttl_seconds=900)

    assert client.setex_calls == [("login:user:ana@example.com", 900, '{"id": "user-1"}')]
    assert cache._fallback_cache.get("login:user:ana@example.com") == {"id": "user-1"}


def test_redis_cache_uses_fallback_when_client_fails():
    client = MockRedisClient(raise_on_get=True)
    fallback = TTLMemoryCache()
    fallback.set("login:user:ana@example.com", {"id": "fallback-user"}, ttl_seconds=900)
    cache = RedisCache("rediss://example.com", fallback_cache=fallback)
    cache._client = client

    assert cache.get("login:user:ana@example.com") == {"id": "fallback-user"}


class MockRedisClient:
    def __init__(self, raise_on_get=False):
        self.raise_on_get = raise_on_get
        self.values = {}
        self.setex_calls = []
        self.deleted_keys = []

    def get(self, key):
        if self.raise_on_get:
            raise RuntimeError("redis unavailable")
        return self.values.get(key)

    def setex(self, key, ttl_seconds, value):
        self.setex_calls.append((key, ttl_seconds, value))
        self.values[key] = value

    def delete(self, key):
        self.deleted_keys.append(key)
        self.values.pop(key, None)
