from abc import ABC, abstractmethod
from datetime import datetime

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.scheduled_job import ScheduledJob, ScheduledJobStatus


class ScheduledJobRepository(ABC):
    @abstractmethod
    async def create(self, job: ScheduledJob) -> ScheduledJob:
        raise NotImplementedError

    @abstractmethod
    async def claim_due(self, now: datetime, limit: int = 10) -> list[ScheduledJob]:
        raise NotImplementedError

    @abstractmethod
    async def update(self, job: ScheduledJob) -> ScheduledJob:
        raise NotImplementedError


class MongoScheduledJobRepository(ScheduledJobRepository):
    def __init__(self, database: AsyncIOMotorDatabase) -> None:
        self.collection = database.scheduled_jobs

    async def create(self, job: ScheduledJob) -> ScheduledJob:
        await self.collection.insert_one(job.model_dump())
        return job

    async def claim_due(self, now: datetime, limit: int = 10) -> list[ScheduledJob]:
        cursor = self.collection.find(
            {"status": ScheduledJobStatus.PENDING, "run_at": {"$lte": now}}
        ).limit(limit)
        documents = await cursor.to_list(length=limit)
        jobs: list[ScheduledJob] = []
        for document in documents:
            result = await self.collection.update_one(
                {"id": document["id"], "status": ScheduledJobStatus.PENDING},
                {
                    "$set": {"status": ScheduledJobStatus.PROCESSING, "locked_at": now},
                    "$inc": {"revision": 1, "attempts": 1},
                },
            )
            if result.modified_count == 1:
                claimed = await self.collection.find_one({"id": document["id"]})
                if claimed:
                    jobs.append(ScheduledJob(**claimed))
        return jobs

    async def update(self, job: ScheduledJob) -> ScheduledJob:
        await self.collection.replace_one({"id": job.id}, job.model_dump())
        return job
