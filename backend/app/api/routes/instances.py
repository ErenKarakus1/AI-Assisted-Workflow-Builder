from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import (
    current_user_dependency,
    instance_event_repository_dependency,
    organization_member_repository_dependency,
    workflow_instance_repository_dependency,
    workflow_repository_dependency,
)
from app.domain.instances.repository import InstanceEventRepository, WorkflowInstanceRepository
from app.domain.instances.service import (
    WorkflowInstanceNotFoundError,
    WorkflowInstanceService,
    WorkflowNotActiveError,
)
from app.domain.orgs.repository import OrganizationMemberRepository
from app.domain.orgs.service import OrganizationAccessDeniedError
from app.domain.workflows.repository import WorkflowRepository
from app.models.user import User
from app.schemas.instance import InstanceEventRead, WorkflowInstanceCreate, WorkflowInstanceRead

router = APIRouter(prefix="/orgs/{organization_id}", tags=["instances"])


def instance_service(
    workflows: Annotated[WorkflowRepository, Depends(workflow_repository_dependency)],
    instances: Annotated[WorkflowInstanceRepository, Depends(workflow_instance_repository_dependency)],
    events: Annotated[InstanceEventRepository, Depends(instance_event_repository_dependency)],
    members: Annotated[OrganizationMemberRepository, Depends(organization_member_repository_dependency)],
) -> WorkflowInstanceService:
    return WorkflowInstanceService(workflows, instances, events, members)


@router.post(
    "/workflows/{workflow_id}/instances",
    response_model=WorkflowInstanceRead,
    status_code=status.HTTP_201_CREATED,
)
async def start_workflow_instance(
    organization_id: str,
    workflow_id: str,
    payload: WorkflowInstanceCreate,
    current_user: Annotated[User, Depends(current_user_dependency)],
    service: Annotated[WorkflowInstanceService, Depends(instance_service)],
) -> WorkflowInstanceRead:
    try:
        return await service.start(organization_id, workflow_id, payload, current_user)
    except OrganizationAccessDeniedError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Organization access denied") from exc
    except WorkflowNotActiveError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Workflow is not active") from exc
    except WorkflowInstanceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found") from exc


@router.get("/instances/{instance_id}", response_model=WorkflowInstanceRead)
async def get_workflow_instance(
    organization_id: str,
    instance_id: str,
    current_user: Annotated[User, Depends(current_user_dependency)],
    service: Annotated[WorkflowInstanceService, Depends(instance_service)],
) -> WorkflowInstanceRead:
    try:
        return await service.get(organization_id, instance_id, current_user)
    except OrganizationAccessDeniedError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Organization access denied") from exc
    except WorkflowInstanceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Instance not found") from exc


@router.get("/instances/{instance_id}/events", response_model=list[InstanceEventRead])
async def list_workflow_instance_events(
    organization_id: str,
    instance_id: str,
    current_user: Annotated[User, Depends(current_user_dependency)],
    service: Annotated[WorkflowInstanceService, Depends(instance_service)],
) -> list[InstanceEventRead]:
    try:
        return await service.list_events(organization_id, instance_id, current_user)
    except OrganizationAccessDeniedError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Organization access denied") from exc
    except WorkflowInstanceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Instance not found") from exc

