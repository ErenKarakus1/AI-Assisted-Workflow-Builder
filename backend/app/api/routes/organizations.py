from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import (
    current_user_dependency,
    instance_event_repository_dependency,
    organization_member_repository_dependency,
    organization_repository_dependency,
    scheduled_job_repository_dependency,
    task_repository_dependency,
    user_repository_dependency,
    workflow_instance_repository_dependency,
    workflow_repository_dependency,
)
from app.core.rate_limit import rate_limit
from app.domain.auth.repository import UserRepository
from app.domain.instances.repository import InstanceEventRepository, WorkflowInstanceRepository
from app.domain.orgs.repository import OrganizationMemberRepository, OrganizationRepository
from app.domain.orgs.service import (
    OrganizationAccessDeniedError,
    OrganizationConflictError,
    OrganizationMemberConflictError,
    OrganizationMemberNotFoundError,
    OrganizationNotFoundError,
    OrganizationService,
)
from app.domain.scheduling.repository import ScheduledJobRepository
from app.domain.tasks.repository import TaskRepository
from app.domain.tasks.service import TaskService
from app.domain.workflows.repository import WorkflowRepository
from app.models.instance import WorkflowInstanceStatus
from app.models.task import TaskStatus
from app.models.user import User
from app.models.workflow import WorkflowStatus
from app.schemas.organization import (
    DashboardStatsRead,
    OrganizationCreate,
    OrganizationMemberCreate,
    OrganizationMemberRead,
    OrganizationRead,
)

router = APIRouter(prefix="/orgs", tags=["organizations"])


@router.post("", response_model=OrganizationRead, status_code=status.HTTP_201_CREATED)
async def create_organization(
    payload: OrganizationCreate,
    _rate_limit: Annotated[None, Depends(rate_limit("orgs:create", limit=20, window_seconds=60))],
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


@router.get("/dashboard/stats", response_model=DashboardStatsRead)
async def get_dashboard_stats(
    current_user: Annotated[User, Depends(current_user_dependency)],
    organizations: Annotated[OrganizationRepository, Depends(organization_repository_dependency)],
    members: Annotated[OrganizationMemberRepository, Depends(organization_member_repository_dependency)],
    workflows: Annotated[WorkflowRepository, Depends(workflow_repository_dependency)],
    instances: Annotated[WorkflowInstanceRepository, Depends(workflow_instance_repository_dependency)],
    tasks: Annotated[TaskRepository, Depends(task_repository_dependency)],
    events: Annotated[InstanceEventRepository, Depends(instance_event_repository_dependency)],
    jobs: Annotated[ScheduledJobRepository, Depends(scheduled_job_repository_dependency)],
) -> DashboardStatsRead:
    user_organizations = await OrganizationService(organizations, members).list_for_user(current_user)
    task_service = TaskService(tasks, workflows, instances, events, members, jobs)
    workflow_count = 0
    active_workflow_count = 0
    pending_approval_count = 0
    run_count = 0
    waiting_run_count = 0

    for organization in user_organizations:
        workflow_count += await workflows.count_by_organization(organization.id)
        active_workflow_count += await workflows.count_by_organization(organization.id, WorkflowStatus.ACTIVE)
        pending_approval_count += await task_service.count_for_org(organization.id, current_user, TaskStatus.PENDING)
        run_count += await instances.count_by_organization(organization.id)
        waiting_run_count += await instances.count_by_organization(organization.id, WorkflowInstanceStatus.WAITING)

    return DashboardStatsRead(
        organizations=len(user_organizations),
        workflows=workflow_count,
        active_workflows=active_workflow_count,
        pending_approvals=pending_approval_count,
        runs=run_count,
        waiting_runs=waiting_run_count,
    )


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


@router.delete("/{organization_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_organization(
    organization_id: str,
    _rate_limit: Annotated[None, Depends(rate_limit("orgs:delete", limit=10, window_seconds=60))],
    current_user: Annotated[User, Depends(current_user_dependency)],
    organizations: Annotated[OrganizationRepository, Depends(organization_repository_dependency)],
    members: Annotated[OrganizationMemberRepository, Depends(organization_member_repository_dependency)],
    workflows: Annotated[WorkflowRepository, Depends(workflow_repository_dependency)],
    instances: Annotated[WorkflowInstanceRepository, Depends(workflow_instance_repository_dependency)],
    events: Annotated[InstanceEventRepository, Depends(instance_event_repository_dependency)],
    tasks: Annotated[TaskRepository, Depends(task_repository_dependency)],
    jobs: Annotated[ScheduledJobRepository, Depends(scheduled_job_repository_dependency)],
) -> None:
    try:
        await OrganizationService(organizations, members).delete(
            organization_id,
            current_user,
            workflows,
            instances,
            events,
            tasks,
            jobs,
        )
    except OrganizationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        ) from exc
    except OrganizationAccessDeniedError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only organization owners can delete organizations",
        ) from exc


@router.get("/{organization_id}/members", response_model=list[OrganizationMemberRead])
async def list_organization_members(
    organization_id: str,
    current_user: Annotated[User, Depends(current_user_dependency)],
    organizations: Annotated[OrganizationRepository, Depends(organization_repository_dependency)],
    members: Annotated[OrganizationMemberRepository, Depends(organization_member_repository_dependency)],
    users: Annotated[UserRepository, Depends(user_repository_dependency)],
) -> list[OrganizationMemberRead]:
    try:
        return await OrganizationService(organizations, members).list_members(
            organization_id,
            current_user,
            users,
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


@router.post("/{organization_id}/members", response_model=OrganizationMemberRead, status_code=status.HTTP_201_CREATED)
async def add_organization_member(
    organization_id: str,
    payload: OrganizationMemberCreate,
    _rate_limit: Annotated[None, Depends(rate_limit("orgs:members:create", limit=30, window_seconds=60))],
    current_user: Annotated[User, Depends(current_user_dependency)],
    organizations: Annotated[OrganizationRepository, Depends(organization_repository_dependency)],
    members: Annotated[OrganizationMemberRepository, Depends(organization_member_repository_dependency)],
    users: Annotated[UserRepository, Depends(user_repository_dependency)],
) -> OrganizationMemberRead:
    try:
        return await OrganizationService(organizations, members).add_member(
            organization_id,
            payload,
            current_user,
            users,
        )
    except OrganizationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        ) from exc
    except OrganizationMemberNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User must register before they can be added to an organization",
        ) from exc
    except OrganizationMemberConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User is already a member of this organization",
        ) from exc
    except OrganizationAccessDeniedError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Organization access denied",
        ) from exc


@router.delete("/{organization_id}/members/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_organization_member(
    organization_id: str,
    member_id: str,
    _rate_limit: Annotated[None, Depends(rate_limit("orgs:members:delete", limit=30, window_seconds=60))],
    current_user: Annotated[User, Depends(current_user_dependency)],
    organizations: Annotated[OrganizationRepository, Depends(organization_repository_dependency)],
    members: Annotated[OrganizationMemberRepository, Depends(organization_member_repository_dependency)],
) -> None:
    try:
        await OrganizationService(organizations, members).remove_member(
            organization_id,
            member_id,
            current_user,
        )
    except OrganizationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        ) from exc
    except OrganizationMemberNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization member not found",
        ) from exc
    except OrganizationConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot remove the last organization owner",
        ) from exc
    except OrganizationAccessDeniedError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Organization access denied",
        ) from exc
