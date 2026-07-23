from datetime import UTC, datetime

from app.domain.instances.repository import InstanceEventRepository, WorkflowInstanceRepository
from app.domain.scheduling.repository import ScheduledJobRepository
from app.domain.workflows.repository import WorkflowRepository
from app.engine.runner import WorkflowEngine
from app.models.scheduled_job import ScheduledJobStatus, ScheduledJobType


class SchedulerService:
    def __init__(
        self,
        jobs: ScheduledJobRepository,
        workflows: WorkflowRepository,
        instances: WorkflowInstanceRepository,
        events: InstanceEventRepository,
    ) -> None:
        self.jobs = jobs
        self.workflows = workflows
        self.instances = instances
        self.events = events

    async def process_due_jobs(self, now: datetime | None = None, limit: int = 10) -> int:
        current_time = now or datetime.now(UTC)
        jobs = await self.jobs.claim_due(current_time, limit)
        completed_count = 0

        for job in jobs:
            try:
                if job.type != ScheduledJobType.DELAY:
                    continue
                workflow = await self.workflows.get_by_id(job.workflow_id)
                instance = await self.instances.get_by_id(job.instance_id)
                if not workflow or not instance:
                    job.status = ScheduledJobStatus.FAILED
                    await self.jobs.update(job)
                    continue

                emitted_events = await WorkflowEngine().resume_after_delay(
                    workflow,
                    instance,
                    job.node_id,
                )
                for event in emitted_events:
                    await self.events.append(event)
                await self.instances.update(instance)

                job.status = ScheduledJobStatus.COMPLETED
                job.completed_at = current_time
                job.revision += 1
                await self.jobs.update(job)
                completed_count += 1
            except Exception: # noqa: BLE001
                job.status = ScheduledJobStatus.FAILED
                job.revision += 1
                await self.jobs.update(job)

        return completed_count
