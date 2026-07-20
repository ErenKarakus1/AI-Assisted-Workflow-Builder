from app.domain.auth.repository import UserRepository
from app.domain.orgs.repository import OrganizationMemberRepository, OrganizationRepository
from app.domain.workflows.repository import WorkflowRepository
from app.models.organization import Organization, OrganizationMember
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
