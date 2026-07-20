from datetime import UTC, datetime

from app.domain.instances.repository import InstanceEventRepository, WorkflowInstanceRepository
from app.domain.orgs.repository import OrganizationMemberRepository
from app.domain.orgs.service import OrganizationAccessDeniedError
from app.domain.scheduling.repository import ScheduledJobRepository
from app.domain.tasks.repository import TaskRepository
from app.domain.workflows.repository import WorkflowRepository
from app.engine.runner import WorkflowEngine
from app.models.instance import InstanceEvent, InstanceEventType, WorkflowInstanceStatus
from app.models.task import Task, TaskDecision, TaskStatus
from app.models.user import User
from app.schemas.task import TaskRead


class TaskNotFoundError(Exception):
    pass


class TaskConflictError(Exception):
    pass


class TaskUnauthorizedError(Exception):
    pass


class TaskService:
    def __init__(
        self,
        tasks: TaskRepository,
        workflows: WorkflowRepository,
        instances: WorkflowInstanceRepository,
        events: InstanceEventRepository,
        members: OrganizationMemberRepository,
        jobs: ScheduledJobRepository,
    ) -> None:
        self.tasks = tasks
        self.workflows = workflows
        self.instances = instances
        self.events = events
        self.members = members
        self.jobs = jobs

    async def list_for_org(self, organization_id: str, user: User) -> list[TaskRead]:
        await self._ensure_membership(organization_id, user)
        return [self._read(task) for task in await self.tasks.list_by_organization(organization_id)]

    async def get(self, organization_id: str, task_id: str, user: User) -> TaskRead:
        task = await self._get_for_org(organization_id, task_id, user)
        return self._read(task)

    async def approve(self, organization_id: str, task_id: str, revision: int, user: User) -> TaskRead:
        return await self._decide(organization_id, task_id, revision, user, TaskDecision.APPROVE)

    async def reject(self, organization_id: str, task_id: str, revision: int, user: User) -> TaskRead:
        return await self._decide(organization_id, task_id, revision, user, TaskDecision.REJECT)

    async def _decide(
        self,
        organization_id: str,
        task_id: str,
        revision: int,
        user: User,
        decision: TaskDecision,
    ) -> TaskRead:
        task = await self._get_for_org(organization_id, task_id, user)
        if task.assigned_user_id and task.assigned_user_id != user.id:
            raise TaskUnauthorizedError
        membership = await self.members.get_by_user_and_org(user.id, organization_id)
        if task.assigned_role and (not membership or membership.role != task.assigned_role):
            raise TaskUnauthorizedError
        if task.status != TaskStatus.PENDING or task.revision != revision:
            raise TaskConflictError

        instance = await self.instances.get_by_id(task.instance_id)
        workflow = await self.workflows.get_by_id(task.workflow_id)
        if not instance or not workflow or instance.status != WorkflowInstanceStatus.WAITING:
            raise TaskConflictError

        task.status = TaskStatus.COMPLETED
        task.decision = decision
        task.completed_by_user_id = user.id
        task.completed_at = datetime.now(UTC)
        task.revision += 1
        await self.tasks.update(task)
        await self.events.append(
            InstanceEvent(
                organization_id=organization_id,
                instance_id=task.instance_id,
                workflow_id=task.workflow_id,
                type=InstanceEventType.TASK_APPROVED
                if decision == TaskDecision.APPROVE
                else InstanceEventType.TASK_REJECTED,
                node_id=task.node_id,
                data={"task_id": task.id},
            )
        )

        created_jobs = []
        emitted_events = await WorkflowEngine(created_jobs=created_jobs).resume_from_decision(
            workflow,
            instance,
            task.node_id,
            decision.value,
        )
        for job in created_jobs:
            await self.jobs.create(job)
        for event in emitted_events:
            await self.events.append(event)
        await self.instances.update(instance)
        return self._read(task)

    async def _get_for_org(self, organization_id: str, task_id: str, user: User) -> Task:
        await self._ensure_membership(organization_id, user)
        task = await self.tasks.get_by_id(task_id)
        if not task or task.organization_id != organization_id:
            raise TaskNotFoundError
        return task

    async def _ensure_membership(self, organization_id: str, user: User) -> None:
        membership = await self.members.get_by_user_and_org(user.id, organization_id)
        if not membership:
            raise OrganizationAccessDeniedError

    def _read(self, task: Task) -> TaskRead:
        return TaskRead(
            id=task.id,
            organization_id=task.organization_id,
            workflow_id=task.workflow_id,
            instance_id=task.instance_id,
            node_id=task.node_id,
            status=task.status,
            assigned_user_id=task.assigned_user_id,
            assigned_role=task.assigned_role,
            decision=task.decision,
            completed_by_user_id=task.completed_by_user_id,
            revision=task.revision,
        )
