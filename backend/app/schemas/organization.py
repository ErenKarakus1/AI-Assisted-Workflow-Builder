from pydantic import BaseModel, Field

from app.models.organization import OrganizationRole


class OrganizationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class OrganizationMemberCreate(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    role: OrganizationRole


class OrganizationRead(BaseModel):
    id: str
    name: str
    role: OrganizationRole


class OrganizationMemberRead(BaseModel):
    id: str
    user_id: str
    email: str
    full_name: str
    role: OrganizationRole
