import asyncio

from app.core.config import settings
from app.db.mongo import close_database, ensure_indexes, get_database
from app.domain.instances.repository import (
    MongoInstanceEventRepository,
    MongoWorkflowInstanceRepository,
)
from app.domain.scheduling.repository import MongoScheduledJobRepository
from app.domain.scheduling.service import SchedulerService
from app.domain.workflows.repository import MongoWorkflowRepository


async def run_once() -> int:
    database = get_database()
    return await SchedulerService(
        jobs=MongoScheduledJobRepository(database),
        workflows=MongoWorkflowRepository(database),
        instances=MongoWorkflowInstanceRepository(database),
        events=MongoInstanceEventRepository(database),
    ).process_due_jobs()


async def run_forever() -> None:
    await ensure_indexes()
    database = get_database()
    service = SchedulerService(
        jobs=MongoScheduledJobRepository(database),
        workflows=MongoWorkflowRepository(database),
        instances=MongoWorkflowInstanceRepository(database),
        events=MongoInstanceEventRepository(database),
    )

    try:
        while True:
            await service.process_due_jobs()
            await asyncio.sleep(settings.scheduler_poll_seconds)
    finally:
        await close_database()


if __name__ == "__main__":
    asyncio.run(run_forever())
