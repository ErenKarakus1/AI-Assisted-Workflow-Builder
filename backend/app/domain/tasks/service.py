from datetime import UTC, datetime

from app.domain.instances.repository import InstanceEventRepository, WorkflowInstanceRepository
from app.domain.orgs.repository import OrganizationMemberRepository
from app.domain.orgs.service import OrganizationAccessDeniedError
from app.domain.scheduling.repository import ScheduledJobRepository
from app.domain.tasks.repository import TaskRepository
from app.domain.workflows.repository import WorkflowRepository
from app.engine.runner import WorkflowEngine
from app.models.instance import InstanceEvent, InstanceEventType, WorkflowInstanceStatus
from app.models.organization import OrganizationRole
from app.models.task import Task, TaskDecision, TaskStatus
from app.models.user import User
from app.schemas.task import TaskPageRead, TaskRead


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

    async def list_for_org(
        self,
        organization_id: str,
        user: User,
        status: TaskStatus | None = None,
        limit: int = 50,
        before: datetime | None = None,
        search: str | None = None,
    ) -> TaskPageRead:
        membership = await self._get_membership(organization_id, user)
        page_items: list[Task] = []
        cursor = before
        next_cursor: datetime | None = None
        normalized_search = search.strip().lower() if search else ""

        while len(page_items) <= limit:
            batch = await self.tasks.list_by_organization(organization_id, status, limit + 1, cursor)
            if not batch:
                next_cursor = None
                break

            for task in batch:
                if membership.role not in {OrganizationRole.OWNER, OrganizationRole.ADMIN} and not self._is_task_visible_to_member(
                    task,
                    user.id,
                    membership.role,
                ):
                    continue
                if normalized_search and not await self._task_matches_search(task, normalized_search):
                    continue
                page_items.append(task)
                if len(page_items) > limit:
                    break

            cursor = batch[-1].created_at
            next_cursor = cursor if len(batch) > limit or len(page_items) > limit else None
            if len(batch) <= limit:
                break

        page_items = page_items[:limit]
        if len(page_items) == limit and next_cursor:
            next_cursor = page_items[-1].created_at
        return TaskPageRead(items=[self._read(task) for task in page_items], next_cursor=next_cursor)

    async def count_for_org(
        self,
        organization_id: str,
        user: User,
        status: TaskStatus | None = None,
    ) -> int:
        membership = await self._get_membership(organization_id, user)
        if membership.role in {OrganizationRole.OWNER, OrganizationRole.ADMIN}:
            return await self.tasks.count_by_organization(organization_id, status)
        tasks = await self.tasks.list_by_organization(organization_id, status)
        return len([task for task in tasks if self._is_task_visible_to_member(task, user.id, membership.role)])

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
        if task.assigned_role and (
            not membership or not self._role_assignment_matches(task.assigned_role, membership.role)
        ):
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
                data={"task_id": task.id, "completed_by_user_id": user.id},
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
        await self._get_membership(organization_id, user)

    async def _get_membership(self, organization_id: str, user: User):
        membership = await self.members.get_by_user_and_org(user.id, organization_id)
        if not membership:
            raise OrganizationAccessDeniedError
        return membership

    def _is_task_visible_to_member(self, task: Task, user_id: str, role: OrganizationRole) -> bool:
        if task.assigned_user_id:
            return task.assigned_user_id == user_id
        if task.assigned_role:
            return self._role_assignment_matches(task.assigned_role, role)
        return False

    async def _task_matches_search(self, task: Task, normalized_search: str) -> bool:
        workflow = await self.workflows.get_by_id(task.workflow_id)
        node_label = ""
        if workflow:
            node = next((workflow_node for workflow_node in workflow.nodes if workflow_node.id == task.node_id), None)
            if node:
                label = node.data.get("label")
                if isinstance(label, str | int | float | bool):
                    node_label = str(label)

        searchable_text = " ".join(
            [
                workflow.name if workflow else "",
                node_label,
                task.instance_id,
                task.assigned_role or "",
                task.assigned_user_id or "",
            ]
        ).lower()
        return normalized_search in searchable_text

    def _role_assignment_matches(self, assigned_role: str, role: OrganizationRole) -> bool:
        if assigned_role == "all":
            return True
        if assigned_role == "owner_or_admin":
            return role in {OrganizationRole.OWNER, OrganizationRole.ADMIN}
        return assigned_role == role

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
            created_at=task.created_at,
            completed_at=task.completed_at,
        )
