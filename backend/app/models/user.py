from datetime import UTC, datetime
from uuid import uuid4

from pydantic import BaseModel, EmailStr, Field


class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    email: EmailStr
    hashed_password: str
    full_name: str
    is_active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

