from app.domain.auth.repository import UserRepository
from app.domain.instances.repository import InstanceEventRepository, WorkflowInstanceRepository
from app.domain.orgs.repository import OrganizationMemberRepository, OrganizationRepository
from app.domain.scheduling.repository import ScheduledJobRepository
from app.domain.tasks.repository import TaskRepository
from app.domain.workflows.repository import WorkflowRepository
from app.models.organization import Organization, OrganizationMember, OrganizationRole
from app.models.user import User
from app.schemas.organization import (
    OrganizationCreate,
    OrganizationMemberCreate,
    OrganizationMemberRead,
    OrganizationRead,
)


class OrganizationNotFoundError(Exception):
    pass


class OrganizationAccessDeniedError(Exception):
    pass


class OrganizationMemberNotFoundError(Exception):
    pass


class OrganizationMemberConflictError(Exception):
    pass


class OrganizationConflictError(Exception):
    pass


class OrganizationService:
    def __init__(
        self,
        organizations: OrganizationRepository,
        members: OrganizationMemberRepository,
    ) -> None:
        self.organizations = organizations
        self.members = members

    async def create(self, payload: OrganizationCreate, user: User) -> OrganizationRead:
        organization = Organization(
            name=payload.name.strip(),
            created_by_user_id=user.id,
        )
        await self.organizations.create(organization)
        await self.members.create(
            OrganizationMember(
                organization_id=organization.id,
                user_id=user.id,
                role=OrganizationRole.OWNER,
            )
        )
        return OrganizationRead(id=organization.id, name=organization.name, role=OrganizationRole.OWNER)

    async def list_for_user(self, user: User) -> list[OrganizationRead]:
        memberships = await self.members.list_by_user(user.id)
        result: list[OrganizationRead] = []

        for membership in memberships:
            organization = await self.organizations.get_by_id(membership.organization_id)
            if organization:
                result.append(
                    OrganizationRead(
                        id=organization.id,
                        name=organization.name,
                        role=membership.role,
                    )
                )

        return result

    async def add_member(
        self,
        organization_id: str,
        payload: OrganizationMemberCreate,
        user: User,
        users: UserRepository,
    ) -> OrganizationMemberRead:
        membership = await self.members.get_by_user_and_org(user.id, organization_id)
        if not membership:
            raise OrganizationAccessDeniedError
        if membership.role not in {OrganizationRole.OWNER, OrganizationRole.ADMIN}:
            raise OrganizationAccessDeniedError
        if payload.role == OrganizationRole.OWNER:
            raise OrganizationAccessDeniedError

        organization = await self.organizations.get_by_id(organization_id)
        if not organization:
            raise OrganizationNotFoundError

        target_user = await users.get_by_email(payload.email)
        if not target_user:
            raise OrganizationMemberNotFoundError

        existing_member = await self.members.get_by_user_and_org(target_user.id, organization_id)
        if existing_member:
            raise OrganizationMemberConflictError

        member = await self.members.create(
            OrganizationMember(
                organization_id=organization_id,
                user_id=target_user.id,
                role=payload.role,
            )
        )
        return OrganizationMemberRead(
            id=member.id,
            user_id=member.user_id,
            email=target_user.email,
            full_name=target_user.full_name,
            role=member.role,
        )

    async def remove_member(self, organization_id: str, member_id: str, user: User) -> None:
        actor_membership = await self.members.get_by_user_and_org(user.id, organization_id)
        if not actor_membership:
            raise OrganizationAccessDeniedError
        if actor_membership.role not in {OrganizationRole.OWNER, OrganizationRole.ADMIN}:
            raise OrganizationAccessDeniedError

        organization = await self.organizations.get_by_id(organization_id)
        if not organization:
            raise OrganizationNotFoundError

        target_membership = await self.members.get_by_id(member_id)
        if not target_membership or target_membership.organization_id != organization_id:
            raise OrganizationMemberNotFoundError

        if target_membership.role == OrganizationRole.OWNER and actor_membership.role != OrganizationRole.OWNER:
            raise OrganizationAccessDeniedError

        organization_members = await self.members.list_by_organization(organization_id)
        owner_count = sum(1 for member in organization_members if member.role == OrganizationRole.OWNER)
        if target_membership.role == OrganizationRole.OWNER and owner_count <= 1:
            raise OrganizationConflictError

        await self.members.delete(member_id)

    async def delete(
        self,
        organization_id: str,
        user: User,
        workflows: WorkflowRepository,
        instances: WorkflowInstanceRepository,
        events: InstanceEventRepository,
        tasks: TaskRepository,
        jobs: ScheduledJobRepository,
    ) -> None:
        membership = await self.members.get_by_user_and_org(user.id, organization_id)
        if not membership:
            raise OrganizationAccessDeniedError
        if membership.role != OrganizationRole.OWNER:
            raise OrganizationAccessDeniedError

        organization = await self.organizations.get_by_id(organization_id)
        if not organization:
            raise OrganizationNotFoundError

        await jobs.delete_by_organization(organization_id)
        await tasks.delete_by_organization(organization_id)
        await events.delete_by_organization(organization_id)
        await instances.delete_by_organization(organization_id)
        await workflows.delete_by_organization(organization_id)
        await self.members.delete_by_organization(organization_id)
        await self.organizations.delete(organization_id)

    async def get_for_user(self, organization_id: str, user: User) -> OrganizationRead:
        membership = await self.members.get_by_user_and_org(user.id, organization_id)
        if not membership:
            raise OrganizationAccessDeniedError

        organization = await self.organizations.get_by_id(organization_id)
        if not organization:
            raise OrganizationNotFoundError

        return OrganizationRead(id=organization.id, name=organization.name, role=membership.role)

    async def list_members(
        self,
        organization_id: str,
        user: User,
        users: UserRepository,
    ) -> list[OrganizationMemberRead]:
        membership = await self.members.get_by_user_and_org(user.id, organization_id)
        if not membership:
            raise OrganizationAccessDeniedError

        organization = await self.organizations.get_by_id(organization_id)
        if not organization:
            raise OrganizationNotFoundError

        result: list[OrganizationMemberRead] = []
        for member in await self.members.list_by_organization(organization_id):
            member_user = await users.get_by_id(member.user_id)
            if member_user:
                result.append(
                    OrganizationMemberRead(
                        id=member.id,
                        user_id=member.user_id,
                        email=member_user.email,
                        full_name=member_user.full_name,
                        role=member.role,
                    )
                )

        return result
