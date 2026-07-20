from abc import ABC, abstractmethod

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.user import User


class UserRepository(ABC):
    @abstractmethod
    async def create(self, user: User) -> User:
        raise NotImplementedError

    @abstractmethod
    async def get_by_email(self, email: str) -> User | None:
        raise NotImplementedError

    @abstractmethod
    async def get_by_id(self, user_id: str) -> User | None:
        raise NotImplementedError


class MongoUserRepository(UserRepository):
    def __init__(self, database: AsyncIOMotorDatabase) -> None:
        self.collection = database.users

    async def create(self, user: User) -> User:
        await self.collection.insert_one(user.model_dump())
        return user

    async def get_by_email(self, email: str) -> User | None:
        document = await self.collection.find_one({"email": email.lower()})
        return User(**document) if document else None

    async def get_by_id(self, user_id: str) -> User | None:
        document = await self.collection.find_one({"id": user_id})
        return User(**document) if document else None

