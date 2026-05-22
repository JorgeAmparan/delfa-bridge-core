import os
import json
from dotenv import load_dotenv

load_dotenv()

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")


class RedisClient:
    """Redis client for sessions and caching."""

    def __init__(self, url: str | None = None):
        self.url = url or REDIS_URL
        self._client = None

    def _get_client(self):
        if self._client is None:
            import redis
            self._client = redis.from_url(self.url, decode_responses=True)
        return self._client

    def get(self, key: str) -> str | None:
        return self._get_client().get(key)

    def set(self, key: str, value: str, ttl: int | None = None):
        client = self._get_client()
        if ttl:
            client.setex(key, ttl, value)
        else:
            client.set(key, value)

    def get_json(self, key: str) -> dict | None:
        raw = self.get(key)
        if raw:
            return json.loads(raw)
        return None

    def set_json(self, key: str, value: dict, ttl: int | None = None):
        self.set(key, json.dumps(value), ttl=ttl)

    def delete(self, key: str):
        self._get_client().delete(key)

    def health(self) -> bool:
        try:
            return self._get_client().ping()
        except Exception:
            return False


redis_client = RedisClient()
