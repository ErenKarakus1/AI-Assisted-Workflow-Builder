from abc import ABC, abstractmethod

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.organization import Organization, OrganizationMember


class OrganizationRepository(ABC):
    @abstractmethod
    async def create(self, organization: Organization) -> Organization:
        raise NotImplementedError

    @abstractmethod
    async def get_by_id(self, organization_id: str) -> Organization | None:
        raise NotImplementedError

    @abstractmethod
    async def delete(self, organization_id: str) -> None:
        raise NotImplementedError


class OrganizationMemberRepository(ABC):
    @abstractmethod
    async def create(self, member: OrganizationMember) -> OrganizationMember:
        raise NotImplementedError

    @abstractmethod
    async def get_by_user_and_org(
        self,
        user_id: str,
        organization_id: str,
    ) -> OrganizationMember | None:
        raise NotImplementedError

    @abstractmethod
    async def list_by_user(self, user_id: str) -> list[OrganizationMember]:
        raise NotImplementedError

    @abstractmethod
    async def list_by_organization(self, organization_id: str) -> list[OrganizationMember]:
        raise NotImplementedError

    @abstractmethod
    async def get_by_id(self, member_id: str) -> OrganizationMember | None:
        raise NotImplementedError

    @abstractmethod
    async def delete(self, member_id: str) -> None:
        raise NotImplementedError

    @abstractmethod
    async def delete_by_organization(self, organization_id: str) -> None:
        raise NotImplementedError


class MongoOrganizationRepository(OrganizationRepository):
    def __init__(self, database: AsyncIOMotorDatabase) -> None:
        self.collection = database.organizations

    async def create(self, organization: Organization) -> Organization:
        await self.collection.insert_one(organization.model_dump())
        return organization

    async def get_by_id(self, organization_id: str) -> Organization | None:
        document = await self.collection.find_one({"id": organization_id})
        return Organization(**document) if document else None

    async def delete(self, organization_id: str) -> None:
        await self.collection.delete_one({"id": organization_id})


class MongoOrganizationMemberRepository(OrganizationMemberRepository):
    def __init__(self, database: AsyncIOMotorDatabase) -> None:
        self.collection = database.organization_members

    async def create(self, member: OrganizationMember) -> OrganizationMember:
        await self.collection.insert_one(member.model_dump())
        return member

    async def get_by_user_and_org(
        self,
        user_id: str,
        organization_id: str,
    ) -> OrganizationMember | None:
        document = await self.collection.find_one(
            {"user_id": user_id, "organization_id": organization_id}
        )
        return OrganizationMember(**document) if document else None

    async def list_by_user(self, user_id: str) -> list[OrganizationMember]:
        cursor = self.collection.find({"user_id": user_id})
        documents = await cursor.to_list(length=None)
        return [OrganizationMember(**document) for document in documents]

    async def list_by_organization(self, organization_id: str) -> list[OrganizationMember]:
        cursor = self.collection.find({"organization_id": organization_id})
        documents = await cursor.to_list(length=None)
        return [OrganizationMember(**document) for document in documents]

    async def get_by_id(self, member_id: str) -> OrganizationMember | None:
        document = await self.collection.find_one({"id": member_id})
        return OrganizationMember(**document) if document else None

    async def delete(self, member_id: str) -> None:
        await self.collection.delete_one({"id": member_id})

    async def delete_by_organization(self, organization_id: str) -> None:
        await self.collection.delete_many({"organization_id": organization_id})
