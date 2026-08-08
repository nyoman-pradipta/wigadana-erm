"""Redis helper — graceful degradation.

Kalau Redis mati: cache di-skip, nomor antrian fallback ke DB.
Aplikasi tetap jalan (tanpa cache & tanpa nomor antrian realtime).
"""
import json
import logging
from typing import Any

from redis import Redis

from .config import settings

logger = logging.getLogger(__name__)

try:
    _r = Redis.from_url(
        settings.REDIS_URL, decode_responses=True, socket_connect_timeout=1
    )
    _r.ping()
    REDIS_OK = True
except Exception as e:  # noqa: BLE001
    _r = None
    REDIS_OK = False
    logger.warning("Redis tidak tersedia (%s) — cache dimatikan, antrian pakai DB", e)


def redis_available() -> bool:
    return REDIS_OK


def cache_get(key: str) -> Any | None:
    if not REDIS_OK:
        return None
    try:
        raw = _r.get(key)
        return json.loads(raw) if raw else None
    except Exception:  # noqa: BLE001
        return None


def cache_set(key: str, value: Any, ttl: int = 30) -> None:
    if not REDIS_OK:
        return
    try:
        _r.setex(key, ttl, json.dumps(value, default=str))
    except Exception:  # noqa: BLE001
        pass


def cache_delete(key: str) -> None:
    if not REDIS_OK:
        return
    try:
        _r.delete(key)
    except Exception:  # noqa: BLE001
        pass


def cache_delete_prefix(prefix: str) -> None:
    """Hapus semua key yang diawali prefix (scan pattern)."""
    if not REDIS_OK:
        return
    try:
        for k in _r.scan_iter(f"{prefix}*"):
            _r.delete(k)
    except Exception:  # noqa: BLE001
        pass


def next_antrian_counter(key: str) -> int | None:
    """INCR counter Redis. None kalau Redis mati."""
    if not REDIS_OK:
        return None
    try:
        return int(_r.incr(key))
    except Exception:  # noqa: BLE001
        return None


def rate_limit_exceeded(key: str, limit: int, window_seconds: int) -> bool:
    """True kalau jumlah attempt melebihi limit dalam window.

    Setiap panggilan meng-increment counter. Window di-reset dari attempt pertama.
    Redis mati -> selalu False (tidak memblokir, aplikasi tetap jalan).
    """
    if not REDIS_OK:
        return False
    try:
        n = _r.incr(key)
        if n == 1:
            _r.expire(key, window_seconds)
        return n > limit
    except Exception:  # noqa: BLE001
        return False
