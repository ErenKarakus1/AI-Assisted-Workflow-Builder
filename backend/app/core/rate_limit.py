from collections.abc import Awaitable, Callable

import redis.asyncio as redis
from fastapi import HTTPException, Request, status
from redis.exceptions import RedisError

from app.core.config import settings

_redis_client: redis.Redis | None = None


def get_redis_client() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(settings.redis_url, encoding="utf-8", decode_responses=True)
    return _redis_client


async def close_redis_client() -> None:
    global _redis_client
    if _redis_client is not None:
        await _redis_client.aclose()
        _redis_client = None


def rate_limit(
    scope: str,
    limit: int,
    window_seconds: int,
) -> Callable[[Request], Awaitable[None]]:
    async def dependency(request: Request) -> None:
        if not settings.rate_limit_enabled:
            return

        client_host = request.client.host if request.client else "unknown"
        key = f"rate-limit:{scope}:{client_host}"

        try:
            client = get_redis_client()
            count = await client.incr(key)
            if count == 1:
                await client.expire(key, window_seconds)
        except RedisError:
            if settings.rate_limit_fail_open:
                return
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Rate limiting is unavailable",
            )

        if count > limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests. Please try again soon.",
                headers={"Retry-After": str(window_seconds)},
            )

    return dependency
