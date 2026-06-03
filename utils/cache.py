import json
import time

from config.settings import REDIS_SOCKET_TIMEOUT_SECONDS, REDIS_URL


class TTLMemoryCache:
    def __init__(self):
        self._store = {}

    def get(self, key):
        item = self._store.get(key)
        if item is None:
            return None

        expires_at, value = item
        if expires_at <= time.time():
            self._store.pop(key, None)
            return None

        return value

    def set(self, key, value, ttl_seconds):
        self._store[key] = (time.time() + ttl_seconds, value)

    def delete(self, key):
        self._store.pop(key, None)


class RedisCache:
    def __init__(self, url, fallback_cache=None):
        self._client = None
        self._url = url
        self._fallback_cache = fallback_cache or TTLMemoryCache()

    def _get_client(self):
        if self._client is not None:
            return self._client

        try:
            import redis
        except ImportError:
            return None

        self._client = redis.from_url(
            self._url,
            decode_responses=True,
            socket_connect_timeout=REDIS_SOCKET_TIMEOUT_SECONDS,
            socket_timeout=REDIS_SOCKET_TIMEOUT_SECONDS,
        )
        return self._client

    def get(self, key):
        client = self._get_client()
        if client is None:
            return self._fallback_cache.get(key)

        try:
            cached = client.get(key)
        except Exception:
            return self._fallback_cache.get(key)

        if cached is None:
            return None

        try:
            return json.loads(cached)
        except json.JSONDecodeError:
            self.delete(key)
            return None

    def set(self, key, value, ttl_seconds):
        self._fallback_cache.set(key, value, ttl_seconds)

        client = self._get_client()
        if client is None:
            return

        try:
            client.setex(key, ttl_seconds, json.dumps(value))
        except Exception:
            return

    def delete(self, key):
        self._fallback_cache.delete(key)

        client = self._get_client()
        if client is None:
            return

        try:
            client.delete(key)
        except Exception:
            return


login_cache = RedisCache(REDIS_URL) if REDIS_URL else TTLMemoryCache()
