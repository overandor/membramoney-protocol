"""
Redis client wrapper for Membra Money Protocol.
Provides caching and session storage. Disabled if Redis is unavailable.
"""

import os
import json
from typing import Optional, Any


class RedisClient:
    """Redis client wrapper with graceful degradation."""

    def __init__(self, url: Optional[str] = None):
        self.url = url or os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self._client = None
        self._connected = False

    def _connect(self):
        if self._client is not None:
            return
        try:
            import redis
            self._client = redis.from_url(self.url, decode_responses=True)
            self._client.ping()
            self._connected = True
        except (ImportError, Exception):
            self._client = None
            self._connected = False

    def get(self, key: str) -> Optional[str]:
        self._connect()
        if not self._connected:
            return None
        try:
            return self._client.get(key)
        except Exception:
            return None

    def set(self, key: str, value: str, ttl: int = 3600) -> bool:
        self._connect()
        if not self._connected:
            return False
        try:
            self._client.setex(key, ttl, value)
            return True
        except Exception:
            return False

    def delete(self, key: str) -> bool:
        self._connect()
        if not self._connected:
            return False
        try:
            self._client.delete(key)
            return True
        except Exception:
            return False

    def get_json(self, key: str) -> Optional[Any]:
        data = self.get(key)
        if data:
            try:
                return json.loads(data)
            except json.JSONDecodeError:
                return None
        return None

    def set_json(self, key: str, value: Any, ttl: int = 3600) -> bool:
        try:
            return self.set(key, json.dumps(value), ttl)
        except (TypeError, ValueError):
            return False

    def health(self) -> dict:
        self._connect()
        return {
            "connected": self._connected,
            "url": self.url,
        }


# Global instance
redis_client = RedisClient()
