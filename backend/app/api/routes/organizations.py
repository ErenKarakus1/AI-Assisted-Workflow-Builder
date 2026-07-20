from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import (
    current_user_dependency,
    organization_member_repository_dependency,
    organization_repository_dependency,
)
from app.domain.orgs.repository import OrganizationMemberRepository, OrganizationRepository
from app.domain.orgs.service import (
    OrganizationAccessDeniedError,
    OrganizationNotFoundError,
    OrganizationService,
)
from app.models.user import User
from app.schemas.organization import OrganizationCreate, OrganizationRead

router = APIRouter(prefix="/orgs", tags=["organizations"])


@router.post("", response_model=OrganizationRead, status_code=status.HTTP_201_CREATED)
async def create_organization(
    payload: OrganizationCreate,
    current_user: Annotated[User, Depends(current_user_dependency)],
    organizations: Annotated[OrganizationRepository, Depends(organization_repository_dependency)],
    members: Annotated[OrganizationMemberRepository, Depends(organization_member_repository_dependency)],
) -> OrganizationRead:
    return await OrganizationService(organizations, members).create(payload, current_user)


@router.get("", response_model=list[OrganizationRead])
async def list_organizations(
    current_user: Annotated[User, Depends(current_user_dependency)],
    organizations: Annotated[OrganizationRepository, Depends(organization_repository_dependency)],
    members: Annotated[OrganizationMemberRepository, Depends(organization_member_repository_dependency)],
) -> list[OrganizationRead]:
    return await OrganizationService(organizations, members).list_for_user(current_user)


@router.get("/{organization_id}", response_model=OrganizationRead)
async def get_organization(
    organization_id: str,
    current_user: Annotated[User, Depends(current_user_dependency)],
    organizations: Annotated[OrganizationRepository, Depends(organization_repository_dependency)],
    members: Annotated[OrganizationMemberRepository, Depends(organization_member_repository_dependency)],
) -> OrganizationRead:
    try:
        return await OrganizationService(organizations, members).get_for_user(
            organization_id,
            current_user,
        )
    except OrganizationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        ) from exc
    except OrganizationAccessDeniedError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Organization access denied",
        ) from exc

