from datetime import datetime

from app.domain.instances.repository import InstanceEventRepository, WorkflowInstanceRepository
from app.domain.orgs.repository import OrganizationMemberRepository
from app.domain.orgs.service import OrganizationAccessDeniedError
from app.domain.scheduling.repository import ScheduledJobRepository
from app.domain.tasks.repository import TaskRepository
from app.domain.workflows.repository import WorkflowRepository
from app.engine.runner import WorkflowEngine
from app.models.instance import InstanceEvent, WorkflowInstance, WorkflowInstanceStatus
from app.models.user import User
from app.models.workflow import WorkflowStatus
from app.schemas.instance import (
    InstanceEventRead,
    WorkflowInstanceCreate,
    WorkflowInstancePageRead,
    WorkflowInstanceRead,
)


class WorkflowNotActiveError(Exception):
    pass


class WorkflowInstanceNotFoundError(Exception):
    pass


class WorkflowInstanceService:
    def __init__(
        self,
        workflows: WorkflowRepository,
        instances: WorkflowInstanceRepository,
        events: InstanceEventRepository,
        members: OrganizationMemberRepository,
        tasks: TaskRepository,
        jobs: ScheduledJobRepository,
    ) -> None:
        self.workflows = workflows
        self.instances = instances
        self.events = events
        self.members = members
        self.tasks = tasks
        self.jobs = jobs

    async def start(
        self,
        organization_id: str,
        workflow_id: str,
        payload: WorkflowInstanceCreate,
        user: User,
    ) -> WorkflowInstanceRead:
        await self._ensure_membership(organization_id, user)
        workflow = await self.workflows.get_by_id(workflow_id)
        if not workflow or workflow.organization_id != organization_id:
            raise WorkflowInstanceNotFoundError
        if workflow.status != WorkflowStatus.ACTIVE:
            raise WorkflowNotActiveError

        instance = WorkflowInstance(
            organization_id=organization_id,
            workflow_id=workflow.id,
            workflow_revision=workflow.revision,
            workflow_nodes=[node.model_copy(deep=True) for node in workflow.nodes],
            workflow_edges=[edge.model_copy(deep=True) for edge in workflow.edges],
            input=payload.input,
            started_by_user_id=user.id,
        )
        await self.instances.create(instance)
        created_tasks = []
        created_jobs = []
        emitted_events = await WorkflowEngine(created_tasks, created_jobs).run(workflow, instance)
        for task in created_tasks:
            await self.tasks.create(task)
        for job in created_jobs:
            await self.jobs.create(job)
        for event in emitted_events:
            await self.events.append(event)
        return self._read_instance(await self.instances.update(instance))

    async def get(self, organization_id: str, instance_id: str, user: User) -> WorkflowInstanceRead:
        instance = await self._get_for_organization(organization_id, instance_id, user)
        return self._read_instance(instance)

    async def list_for_workflow(
        self,
        organization_id: str,
        workflow_id: str,
        user: User,
    ) -> list[WorkflowInstanceRead]:
        await self._ensure_membership(organization_id, user)
        workflow = await self.workflows.get_by_id(workflow_id)
        if not workflow or workflow.organization_id != organization_id:
            raise WorkflowInstanceNotFoundError

        instances = await self.instances.list_by_workflow(organization_id, workflow_id)
        return [self._read_instance(instance) for instance in instances]

    async def list_for_organization(
        self,
        organization_id: str,
        user: User,
        status: WorkflowInstanceStatus | None = None,
        limit: int = 50,
        before: datetime | None = None,
    ) -> WorkflowInstancePageRead:
        await self._ensure_membership(organization_id, user)
        instances = await self.instances.list_by_organization(organization_id, status, limit + 1, before)
        page_items = instances[:limit]
        next_cursor = page_items[-1].started_at if len(instances) > limit and page_items else None
        return WorkflowInstancePageRead(
            items=[self._read_instance(instance) for instance in page_items],
            next_cursor=next_cursor,
        )

    async def list_events(
        self,
        organization_id: str,
        instance_id: str,
        user: User,
    ) -> list[InstanceEventRead]:
        await self._get_for_organization(organization_id, instance_id, user)
        events = await self.events.list_by_instance(instance_id)
        return [self._read_event(event) for event in events if event.organization_id == organization_id]

    async def _ensure_membership(self, organization_id: str, user: User) -> None:
        membership = await self.members.get_by_user_and_org(user.id, organization_id)
        if not membership:
            raise OrganizationAccessDeniedError

    async def _get_for_organization(
        self,
        organization_id: str,
        instance_id: str,
        user: User,
    ) -> WorkflowInstance:
        await self._ensure_membership(organization_id, user)
        instance = await self.instances.get_by_id(instance_id)
        if not instance or instance.organization_id != organization_id:
            raise WorkflowInstanceNotFoundError
        return instance

    def _read_instance(self, instance: WorkflowInstance) -> WorkflowInstanceRead:
        return WorkflowInstanceRead(
            id=instance.id,
            organization_id=instance.organization_id,
            workflow_id=instance.workflow_id,
            workflow_revision=instance.workflow_revision,
            workflow_nodes=instance.workflow_nodes,
            workflow_edges=instance.workflow_edges,
            status=instance.status,
            active_node_id=instance.active_node_id,
            context=instance.context,
            input=instance.input,
            revision=instance.revision,
            started_by_user_id=instance.started_by_user_id,
            started_at=instance.started_at,
            completed_at=instance.completed_at,
        )

    def _read_event(self, event: InstanceEvent) -> InstanceEventRead:
        return InstanceEventRead(
            id=event.id,
            organization_id=event.organization_id,
            instance_id=event.instance_id,
            workflow_id=event.workflow_id,
            type=event.type,
            node_id=event.node_id,
            data=event.data,
            created_at=event.created_at,
        )
