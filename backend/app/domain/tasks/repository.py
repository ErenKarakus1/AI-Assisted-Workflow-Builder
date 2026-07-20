from abc import ABC, abstractmethod

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.task import Task, TaskStatus


class TaskRepository(ABC):
    @abstractmethod
    async def create(self, task: Task) -> Task:
        raise NotImplementedError

    @abstractmethod
    async def get_by_id(self, task_id: str) -> Task | None:
        raise NotImplementedError

    @abstractmethod
    async def get_pending_by_instance_and_node(self, instance_id: str, node_id: str) -> Task | None:
        raise NotImplementedError

    @abstractmethod
    async def list_by_organization(self, organization_id: str) -> list[Task]:
        raise NotImplementedError

    @abstractmethod
    async def update(self, task: Task) -> Task:
        raise NotImplementedError


class MongoTaskRepository(TaskRepository):
    def __init__(self, database: AsyncIOMotorDatabase) -> None:
        self.collection = database.tasks

    async def create(self, task: Task) -> Task:
        await self.collection.insert_one(task.model_dump())
        return task

    async def get_by_id(self, task_id: str) -> Task | None:
        document = await self.collection.find_one({"id": task_id})
        return Task(**document) if document else None

    async def get_pending_by_instance_and_node(self, instance_id: str, node_id: str) -> Task | None:
        document = await self.collection.find_one(
            {"instance_id": instance_id, "node_id": node_id, "status": TaskStatus.PENDING}
        )
        return Task(**document) if document else None

    async def list_by_organization(self, organization_id: str) -> list[Task]:
        cursor = self.collection.find({"organization_id": organization_id})
        documents = await cursor.to_list(length=None)
        return [Task(**document) for document in documents]

    async def update(self, task: Task) -> Task:
        await self.collection.replace_one({"id": task.id}, task.model_dump())
        return task
