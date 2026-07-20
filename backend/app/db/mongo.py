from collections.abc import AsyncIterator

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import ASCENDING

from app.core.config import settings

client = AsyncIOMotorClient(settings.mongodb_url)


def get_database() -> AsyncIOMotorDatabase:
    return client[settings.mongodb_database]


async def database_dependency() -> AsyncIterator[AsyncIOMotorDatabase]:
    yield get_database()


async def close_database() -> None:
    client.close()


async def ensure_indexes() -> None:
    database = get_database()

    await database.users.create_index([("email", ASCENDING)], unique=True)
    await database.organization_members.create_index(
        [("user_id", ASCENDING), ("organization_id", ASCENDING)],
        unique=True,
    )
    await database.organization_members.create_index([("organization_id", ASCENDING)])
    await database.workflows.create_index([("organization_id", ASCENDING), ("id", ASCENDING)])
    await database.workflow_instances.create_index([("organization_id", ASCENDING), ("id", ASCENDING)])
    await database.tasks.create_index([("organization_id", ASCENDING), ("status", ASCENDING)])
    await database.tasks.create_index(
        [("instance_id", ASCENDING), ("node_id", ASCENDING), ("status", ASCENDING)]
    )
    await database.scheduled_jobs.create_index(
        [("status", ASCENDING), ("run_at", ASCENDING), ("type", ASCENDING)]
    )
    await database.instance_events.create_index([("instance_id", ASCENDING), ("created_at", ASCENDING)])
