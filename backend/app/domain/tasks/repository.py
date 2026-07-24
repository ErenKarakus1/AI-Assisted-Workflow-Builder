from abc import ABC, abstractmethod
from datetime import datetime

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
    async def list_by_organization(
        self,
        organization_id: str,
        status: TaskStatus | None = None,
        limit: int | None = None,
        before: datetime | None = None,
        search: str | None = None,
    ) -> list[Task]:
        raise NotImplementedError

    @abstractmethod
    async def count_by_organization(
        self,
        organization_id: str,
        status: TaskStatus | None = None,
    ) -> int:
        raise NotImplementedError

    @abstractmethod
    async def update(self, task: Task) -> Task:
        raise NotImplementedError

    @abstractmethod
    async def delete_by_organization(self, organization_id: str) -> None:
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

    async def list_by_organization(
        self,
        organization_id: str,
        status: TaskStatus | None = None,
        limit: int | None = None,
        before: datetime | None = None,
        search: str | None = None,
    ) -> list[Task]:
        query = {"organization_id": organization_id}
        if status:
            query["status"] = status
        if before:
            query["created_at"] = {"$lt": before}
        if search:
            query["$or"] = [
                {"instance_id": {"$regex": search, "$options": "i"}},
                {"assigned_role": {"$regex": search, "$options": "i"}},
                {"assigned_user_id": {"$regex": search, "$options": "i"}},
            ]
        cursor = self.collection.find(query).sort("created_at", -1)
        documents = await cursor.to_list(length=limit)
        return [Task(**document) for document in documents]

    async def count_by_organization(
        self,
        organization_id: str,
        status: TaskStatus | None = None,
    ) -> int:
        query = {"organization_id": organization_id}
        if status:
            query["status"] = status
        return await self.collection.count_documents(query)

    async def update(self, task: Task) -> Task:
        await self.collection.replace_one({"id": task.id}, task.model_dump())
        return task

    async def delete_by_organization(self, organization_id: str) -> None:
        await self.collection.delete_many({"organization_id": organization_id})
