from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from redis.exceptions import RedisError

from app.core import rate_limit as rate_limit_module
from app.core.config import settings


class FakeRedis:
    def __init__(self) -> None:
        self.counts: dict[str, int] = {}
        self.expirations: dict[str, int] = {}

    async def incr(self, key: str) -> int:
        self.counts[key] = self.counts.get(key, 0) + 1
        return self.counts[key]

    async def expire(self, key: str, seconds: int) -> None:
        self.expirations[key] = seconds


class BrokenRedis:
    async def incr(self, key: str) -> int:
        raise RedisError("redis unavailable")


@pytest.fixture(autouse=True)
def reset_rate_limit_settings(monkeypatch):
    monkeypatch.setattr(settings, "rate_limit_enabled", True)
    monkeypatch.setattr(settings, "rate_limit_fail_open", True)
    monkeypatch.setattr(rate_limit_module, "_redis_client", None)
    yield
    monkeypatch.setattr(rate_limit_module, "_redis_client", None)


@pytest.mark.anyio
async def test_rate_limit_blocks_after_limit(monkeypatch) -> None:
    fake_redis = FakeRedis()
    monkeypatch.setattr(rate_limit_module, "_redis_client", fake_redis)
    dependency = rate_limit_module.rate_limit("test", limit=2, window_seconds=60)
    request = SimpleNamespace(client=SimpleNamespace(host="127.0.0.1"))

    await dependency(request)
    await dependency(request)

    with pytest.raises(HTTPException) as exc_info:
        await dependency(request)

    assert exc_info.value.status_code == 429
    assert fake_redis.expirations["rate-limit:test:127.0.0.1"] == 60


@pytest.mark.anyio
async def test_rate_limit_fails_open_when_configured(monkeypatch) -> None:
    monkeypatch.setattr(rate_limit_module, "_redis_client", BrokenRedis())
    dependency = rate_limit_module.rate_limit("test", limit=2, window_seconds=60)
    request = SimpleNamespace(client=SimpleNamespace(host="127.0.0.1"))

    await dependency(request)
