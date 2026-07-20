from app.domain.auth.repository import UserRepository
from app.domain.orgs.repository import OrganizationMemberRepository, OrganizationRepository
from app.models.organization import Organization, OrganizationMember, OrganizationRole
from app.models.user import User
from app.schemas.organization import OrganizationCreate, OrganizationMemberRead, OrganizationRead


class OrganizationNotFoundError(Exception):
    pass


class OrganizationAccessDeniedError(Exception):
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
