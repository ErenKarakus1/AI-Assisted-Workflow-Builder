import asyncio

from app.db.mongo import get_database
from app.domain.instances.repository import MongoInstanceEventRepository, MongoWorkflowInstanceRepository
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


if __name__ == "__main__":
    processed = asyncio.run(run_once())
    print(f"Processed {processed} scheduled jobs")
