from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.security import decode_token
from app.db.mongo import database_dependency
from app.domain.auth.repository import MongoUserRepository, UserRepository
from app.domain.orgs.repository import (
    MongoOrganizationMemberRepository,
    MongoOrganizationRepository,
    OrganizationMemberRepository,
    OrganizationRepository,
)
from app.domain.workflows.repository import MongoWorkflowRepository, WorkflowRepository
from app.models.user import User

bearer_scheme = HTTPBearer(auto_error=False)


async def user_repository_dependency(
    database: Annotated[AsyncIOMotorDatabase, Depends(database_dependency)],
) -> UserRepository:
    return MongoUserRepository(database)


async def organization_repository_dependency(
    database: Annotated[AsyncIOMotorDatabase, Depends(database_dependency)],
) -> OrganizationRepository:
    return MongoOrganizationRepository(database)


async def organization_member_repository_dependency(
    database: Annotated[AsyncIOMotorDatabase, Depends(database_dependency)],
) -> OrganizationMemberRepository:
    return MongoOrganizationMemberRepository(database)


async def workflow_repository_dependency(
    database: Annotated[AsyncIOMotorDatabase, Depends(database_dependency)],
) -> WorkflowRepository:
    return MongoWorkflowRepository(database)


async def current_user_dependency(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    users: Annotated[UserRepository, Depends(user_repository_dependency)],
) -> User:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token",
        )

    try:
        user_id = decode_token(credentials.credentials, "access")
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
        ) from exc

    user = await users.get_by_id(user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
        )

    return user
