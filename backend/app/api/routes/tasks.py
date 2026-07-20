from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import (
    current_user_dependency,
    instance_event_repository_dependency,
    organization_member_repository_dependency,
    task_repository_dependency,
    workflow_instance_repository_dependency,
    workflow_repository_dependency,
)
from app.domain.instances.repository import InstanceEventRepository, WorkflowInstanceRepository
from app.domain.orgs.repository import OrganizationMemberRepository
from app.domain.orgs.service import OrganizationAccessDeniedError
from app.domain.tasks.repository import TaskRepository
from app.domain.tasks.service import TaskConflictError, TaskNotFoundError, TaskService, TaskUnauthorizedError
from app.domain.workflows.repository import WorkflowRepository
from app.models.user import User
from app.schemas.task import TaskDecisionRequest, TaskRead

router = APIRouter(prefix="/orgs/{organization_id}/tasks", tags=["tasks"])


def task_service(
    tasks: Annotated[TaskRepository, Depends(task_repository_dependency)],
    workflows: Annotated[WorkflowRepository, Depends(workflow_repository_dependency)],
    instances: Annotated[WorkflowInstanceRepository, Depends(workflow_instance_repository_dependency)],
    events: Annotated[InstanceEventRepository, Depends(instance_event_repository_dependency)],
    members: Annotated[OrganizationMemberRepository, Depends(organization_member_repository_dependency)],
) -> TaskService:
    return TaskService(tasks, workflows, instances, events, members)


@router.get("", response_model=list[TaskRead])
async def list_tasks(
    organization_id: str,
    current_user: Annotated[User, Depends(current_user_dependency)],
    service: Annotated[TaskService, Depends(task_service)],
) -> list[TaskRead]:
    try:
        return await service.list_for_org(organization_id, current_user)
    except OrganizationAccessDeniedError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Organization access denied") from exc


@router.get("/{task_id}", response_model=TaskRead)
async def get_task(
    organization_id: str,
    task_id: str,
    current_user: Annotated[User, Depends(current_user_dependency)],
    service: Annotated[TaskService, Depends(task_service)],
) -> TaskRead:
    try:
        return await service.get(organization_id, task_id, current_user)
    except OrganizationAccessDeniedError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Organization access denied") from exc
    except TaskNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found") from exc


@router.post("/{task_id}/approve", response_model=TaskRead)
async def approve_task(
    organization_id: str,
    task_id: str,
    payload: TaskDecisionRequest,
    current_user: Annotated[User, Depends(current_user_dependency)],
    service: Annotated[TaskService, Depends(task_service)],
) -> TaskRead:
    return await decide_task(service.approve, organization_id, task_id, payload, current_user)


@router.post("/{task_id}/reject", response_model=TaskRead)
async def reject_task(
    organization_id: str,
    task_id: str,
    payload: TaskDecisionRequest,
    current_user: Annotated[User, Depends(current_user_dependency)],
    service: Annotated[TaskService, Depends(task_service)],
) -> TaskRead:
    return await decide_task(service.reject, organization_id, task_id, payload, current_user)


async def decide_task(action, organization_id: str, task_id: str, payload: TaskDecisionRequest, user: User) -> TaskRead:
    try:
        return await action(organization_id, task_id, payload.revision, user)
    except OrganizationAccessDeniedError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Organization access denied") from exc
    except TaskUnauthorizedError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Task access denied") from exc
    except TaskNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found") from exc
    except TaskConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Task conflict") from exc
