from abc import ABC, abstractmethod

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.instance import InstanceEvent, WorkflowInstance


class WorkflowInstanceRepository(ABC):
    @abstractmethod
    async def create(self, instance: WorkflowInstance) -> WorkflowInstance:
        raise NotImplementedError

    @abstractmethod
    async def get_by_id(self, instance_id: str) -> WorkflowInstance | None:
        raise NotImplementedError

    @abstractmethod
    async def list_by_workflow(self, organization_id: str, workflow_id: str) -> list[WorkflowInstance]:
        raise NotImplementedError

    @abstractmethod
    async def update(self, instance: WorkflowInstance) -> WorkflowInstance:
        raise NotImplementedError


class InstanceEventRepository(ABC):
    @abstractmethod
    async def append(self, event: InstanceEvent) -> InstanceEvent:
        raise NotImplementedError

    @abstractmethod
    async def list_by_instance(self, instance_id: str) -> list[InstanceEvent]:
        raise NotImplementedError


class MongoWorkflowInstanceRepository(WorkflowInstanceRepository):
    def __init__(self, database: AsyncIOMotorDatabase) -> None:
        self.collection = database.workflow_instances

    async def create(self, instance: WorkflowInstance) -> WorkflowInstance:
        await self.collection.insert_one(instance.model_dump())
        return instance

    async def get_by_id(self, instance_id: str) -> WorkflowInstance | None:
        document = await self.collection.find_one({"id": instance_id})
        return WorkflowInstance(**document) if document else None

    async def list_by_workflow(self, organization_id: str, workflow_id: str) -> list[WorkflowInstance]:
        cursor = self.collection.find(
            {"organization_id": organization_id, "workflow_id": workflow_id}
        ).sort("started_at", -1)
        documents = await cursor.to_list(length=None)
        return [WorkflowInstance(**document) for document in documents]

    async def update(self, instance: WorkflowInstance) -> WorkflowInstance:
        await self.collection.replace_one({"id": instance.id}, instance.model_dump())
        return instance


class MongoInstanceEventRepository(InstanceEventRepository):
    def __init__(self, database: AsyncIOMotorDatabase) -> None:
        self.collection = database.instance_events

    async def append(self, event: InstanceEvent) -> InstanceEvent:
        await self.collection.insert_one(event.model_dump())
        return event

    async def list_by_instance(self, instance_id: str) -> list[InstanceEvent]:
        cursor = self.collection.find({"instance_id": instance_id}).sort("created_at", 1)
        documents = await cursor.to_list(length=None)
        return [InstanceEvent(**document) for document in documents]
