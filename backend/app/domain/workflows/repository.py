from abc import ABC, abstractmethod

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.workflow import Workflow


class WorkflowRepository(ABC):
    @abstractmethod
    async def create(self, workflow: Workflow) -> Workflow:
        raise NotImplementedError

    @abstractmethod
    async def get_by_id(self, workflow_id: str) -> Workflow | None:
        raise NotImplementedError

    @abstractmethod
    async def list_by_organization(self, organization_id: str) -> list[Workflow]:
        raise NotImplementedError

    @abstractmethod
    async def update(self, workflow: Workflow) -> Workflow:
        raise NotImplementedError

    @abstractmethod
    async def delete(self, workflow_id: str) -> None:
        raise NotImplementedError


class MongoWorkflowRepository(WorkflowRepository):
    def __init__(self, database: AsyncIOMotorDatabase) -> None:
        self.collection = database.workflows

    async def create(self, workflow: Workflow) -> Workflow:
        await self.collection.insert_one(workflow.model_dump())
        return workflow

    async def get_by_id(self, workflow_id: str) -> Workflow | None:
        document = await self.collection.find_one({"id": workflow_id})
        return Workflow(**document) if document else None

    async def list_by_organization(self, organization_id: str) -> list[Workflow]:
        cursor = self.collection.find({"organization_id": organization_id})
        documents = await cursor.to_list(length=None)
        return [Workflow(**document) for document in documents]

    async def update(self, workflow: Workflow) -> Workflow:
        await self.collection.replace_one({"id": workflow.id}, workflow.model_dump())
        return workflow

    async def delete(self, workflow_id: str) -> None:
        await self.collection.delete_one({"id": workflow_id})

