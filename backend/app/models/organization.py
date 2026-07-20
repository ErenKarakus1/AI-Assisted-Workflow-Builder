from datetime import UTC, datetime
from enum import StrEnum
from uuid import uuid4

from pydantic import BaseModel, Field


class OrganizationRole(StrEnum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"


class Organization(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    created_by_user_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class OrganizationMember(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    organization_id: str
    user_id: str
    role: OrganizationRole
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

