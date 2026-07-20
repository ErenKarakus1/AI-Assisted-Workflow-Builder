from collections.abc import AsyncIterator

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.core.config import settings

client = AsyncIOMotorClient(settings.mongodb_url)


def get_database() -> AsyncIOMotorDatabase:
    return client[settings.mongodb_database]


async def database_dependency() -> AsyncIterator[AsyncIOMotorDatabase]:
    yield get_database()

