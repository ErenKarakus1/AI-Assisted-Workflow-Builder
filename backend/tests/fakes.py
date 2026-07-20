from app.domain.auth.repository import UserRepository
from app.domain.instances.repository import InstanceEventRepository, WorkflowInstanceRepository
from app.domain.orgs.repository import OrganizationMemberRepository, OrganizationRepository
from app.domain.scheduling.repository import ScheduledJobRepository
from app.domain.tasks.repository import TaskRepository
from app.domain.workflows.repository import WorkflowRepository
from app.models.instance import InstanceEvent, WorkflowInstance
from app.models.organization import Organization, OrganizationMember
from app.models.scheduled_job import ScheduledJob, ScheduledJobStatus
from app.models.task import Task, TaskStatus
from app.models.user import User
from app.models.workflow import Workflow


class InMemoryUserRepository(UserRepository):
    def __init__(self) -> None:
        self.users_by_id: dict[str, User] = {}
        self.users_by_email: dict[str, User] = {}

    async def create(self, user: User) -> User:
        self.users_by_id[user.id] = user
        self.users_by_email[user.email] = user
        return user

    async def get_by_email(self, email: str) -> User | None:
        return self.users_by_email.get(email.lower())

    async def get_by_id(self, user_id: str) -> User | None:
        return self.users_by_id.get(user_id)


class InMemoryOrganizationRepository(OrganizationRepository):
    def __init__(self) -> None:
        self.organizations_by_id: dict[str, Organization] = {}

    async def create(self, organization: Organization) -> Organization:
        self.organizations_by_id[organization.id] = organization
        return organization

    async def get_by_id(self, organization_id: str) -> Organization | None:
        return self.organizations_by_id.get(organization_id)


class InMemoryOrganizationMemberRepository(OrganizationMemberRepository):
    def __init__(self) -> None:
        self.members_by_id: dict[str, OrganizationMember] = {}

    async def create(self, member: OrganizationMember) -> OrganizationMember:
        self.members_by_id[member.id] = member
        return member

    async def get_by_user_and_org(
        self,
        user_id: str,
        organization_id: str,
    ) -> OrganizationMember | None:
        for member in self.members_by_id.values():
            if member.user_id == user_id and member.organization_id == organization_id:
                return member
        return None

    async def list_by_user(self, user_id: str) -> list[OrganizationMember]:
        return [member for member in self.members_by_id.values() if member.user_id == user_id]

    async def list_by_organization(self, organization_id: str) -> list[OrganizationMember]:
        return [
            member
            for member in self.members_by_id.values()
            if member.organization_id == organization_id
        ]


class InMemoryWorkflowRepository(WorkflowRepository):
    def __init__(self) -> None:
        self.workflows_by_id: dict[str, Workflow] = {}

    async def create(self, workflow: Workflow) -> Workflow:
        self.workflows_by_id[workflow.id] = workflow
        return workflow

    async def get_by_id(self, workflow_id: str) -> Workflow | None:
        return self.workflows_by_id.get(workflow_id)

    async def list_by_organization(self, organization_id: str) -> list[Workflow]:
        return [
            workflow
            for workflow in self.workflows_by_id.values()
            if workflow.organization_id == organization_id
        ]

    async def update(self, workflow: Workflow) -> Workflow:
        self.workflows_by_id[workflow.id] = workflow
        return workflow

    async def delete(self, workflow_id: str) -> None:
        self.workflows_by_id.pop(workflow_id, None)


class InMemoryWorkflowInstanceRepository(WorkflowInstanceRepository):
    def __init__(self) -> None:
        self.instances_by_id: dict[str, WorkflowInstance] = {}

    async def create(self, instance: WorkflowInstance) -> WorkflowInstance:
        self.instances_by_id[instance.id] = instance
        return instance

    async def get_by_id(self, instance_id: str) -> WorkflowInstance | None:
        return self.instances_by_id.get(instance_id)

    async def list_by_workflow(self, organization_id: str, workflow_id: str) -> list[WorkflowInstance]:
        return [
            instance
            for instance in self.instances_by_id.values()
            if instance.organization_id == organization_id and instance.workflow_id == workflow_id
        ]

    async def update(self, instance: WorkflowInstance) -> WorkflowInstance:
        self.instances_by_id[instance.id] = instance
        return instance


class InMemoryInstanceEventRepository(InstanceEventRepository):
    def __init__(self) -> None:
        self.events: list[InstanceEvent] = []

    async def append(self, event: InstanceEvent) -> InstanceEvent:
        self.events.append(event)
        return event

    async def list_by_instance(self, instance_id: str) -> list[InstanceEvent]:
        return [event for event in self.events if event.instance_id == instance_id]


class InMemoryTaskRepository(TaskRepository):
    def __init__(self) -> None:
        self.tasks_by_id: dict[str, Task] = {}

    async def create(self, task: Task) -> Task:
        self.tasks_by_id[task.id] = task
        return task

    async def get_by_id(self, task_id: str) -> Task | None:
        return self.tasks_by_id.get(task_id)

    async def get_pending_by_instance_and_node(self, instance_id: str, node_id: str) -> Task | None:
        for task in self.tasks_by_id.values():
            if (
                task.instance_id == instance_id
                and task.node_id == node_id
                and task.status == TaskStatus.PENDING
            ):
                return task
        return None

    async def list_by_organization(self, organization_id: str) -> list[Task]:
        return [task for task in self.tasks_by_id.values() if task.organization_id == organization_id]

    async def update(self, task: Task) -> Task:
        self.tasks_by_id[task.id] = task
        return task


class InMemoryScheduledJobRepository(ScheduledJobRepository):
    def __init__(self) -> None:
        self.jobs_by_id: dict[str, ScheduledJob] = {}

    async def create(self, job: ScheduledJob) -> ScheduledJob:
        self.jobs_by_id[job.id] = job
        return job

    async def claim_due(self, now, limit: int = 10) -> list[ScheduledJob]:
        claimed: list[ScheduledJob] = []
        for job in self.jobs_by_id.values():
            if len(claimed) >= limit:
                break
            if job.status == ScheduledJobStatus.PENDING and job.run_at <= now:
                job.status = ScheduledJobStatus.PROCESSING
                job.locked_at = now
                job.attempts += 1
                job.revision += 1
                claimed.append(job)
        return claimed

    async def update(self, job: ScheduledJob) -> ScheduledJob:
        self.jobs_by_id[job.id] = job
        return job
