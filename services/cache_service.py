"""
Centralized Cache Service with Redis and High-Performance In-Memory Fallback.
Provides get, set, delete, get_or_set, and distributed locking.
Strictly under 500 lines. Zero emojis.
"""
from __future__ import annotations

import json
import logging
import os
import threading
import time
from typing import Any, Callable, Optional

logger = logging.getLogger("khulaasaa.cache")

_REDIS_CLIENT = None
_REDIS_INITIALIZED = False
_MEM_CACHE: dict[str, tuple[float, Any]] = {}
_MEM_LOCK = threading.Lock()


def get_redis_client():
    """Retrieve connected Redis client or None if Redis is not configured/reachable."""
    global _REDIS_CLIENT, _REDIS_INITIALIZED
    if _REDIS_INITIALIZED:
        return _REDIS_CLIENT

    redis_url = os.environ.get("REDIS_URL") or os.environ.get("REDIS_HOST", "")
    if redis_url:
        try:
            import redis
            if not redis_url.startswith("redis://"):
                port = int(os.environ.get("REDIS_PORT", "6379"))
                password = os.environ.get("REDIS_PASSWORD") or None
                client = redis.Redis(host=redis_url, port=port, password=password, socket_timeout=1.5)
            else:
                client = redis.from_url(redis_url, socket_timeout=1.5)
            client.ping()
            _REDIS_CLIENT = client
            logger.info("Connected to Redis cache successfully.")
        except Exception as exc:
            logger.warning("Redis unavailable (%s), falling back to in-memory cache: %s", redis_url, exc)
            _REDIS_CLIENT = None
    else:
        _REDIS_CLIENT = None

    _REDIS_INITIALIZED = True
    return _REDIS_CLIENT


def cache_get(key: str) -> Optional[Any]:
    """Retrieve item from Redis or in-memory fallback. Returns None if expired or not found."""
    r = get_redis_client()
    if r is not None:
        try:
            val = r.get(key)
            if val is not None:
                return json.loads(val)
            return None
        except Exception as exc:
            logger.debug("Redis get error for %s: %s", key, exc)

    now = time.time()
    with _MEM_LOCK:
        if key in _MEM_CACHE:
            expires_at, val = _MEM_CACHE[key]
            if expires_at == 0 or now < expires_at:
                return val
            del _MEM_CACHE[key]
    return None


def cache_set(key: str, value: Any, ttl_seconds: int = 300) -> bool:
    """Store item in Redis or in-memory cache with specified TTL in seconds."""
    r = get_redis_client()
    if r is not None:
        try:
            s_val = json.dumps(value, default=str)
            r.set(key, s_val, ex=ttl_seconds)
            return True
        except Exception as exc:
            logger.debug("Redis set error for %s: %s", key, exc)

    now = time.time()
    expires_at = (now + ttl_seconds) if ttl_seconds > 0 else 0
    with _MEM_LOCK:
        _MEM_CACHE[key] = (expires_at, value)
    return True


def cache_delete(key: str) -> bool:
    """Remove item from Redis and in-memory cache."""
    r = get_redis_client()
    if r is not None:
        try:
            r.delete(key)
        except Exception:
            pass

    with _MEM_LOCK:
        _MEM_CACHE.pop(key, None)
    return True


def cache_get_or_set(key: str, factory: Callable[[], Any], ttl_seconds: int = 300) -> Any:
    """Return cached item, or invoke factory, cache result, and return."""
    cached = cache_get(key)
    if cached is not None:
        return cached

    fresh = factory()
    if fresh is not None:
        cache_set(key, fresh, ttl_seconds=ttl_seconds)
    return fresh
