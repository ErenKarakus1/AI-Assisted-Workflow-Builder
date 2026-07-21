from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.api.dependencies import (
    current_user_dependency,
    organization_member_repository_dependency,
    workflow_repository_dependency,
)
from app.domain.orgs.repository import OrganizationMemberRepository
from app.domain.orgs.service import OrganizationAccessDeniedError
from app.domain.workflows.ai import AIConfigurationError, AIGenerationError, WorkflowAIService
from app.domain.workflows.repository import WorkflowRepository
from app.domain.workflows.service import (
    WorkflowNotFoundError,
    WorkflowRevisionConflictError,
    WorkflowService,
    WorkflowValidationError,
)
from app.models.user import User
from app.schemas.workflow import (
    WorkflowAIAnalyzeRequest,
    WorkflowAIAnalyzeResponse,
    WorkflowAIGenerateRequest,
    WorkflowAIGenerateResponse,
    WorkflowAIStatusResponse,
    WorkflowCreate,
    WorkflowRead,
    WorkflowUpdate,
    WorkflowValidationResult,
)
from app.core.config import settings

router = APIRouter(prefix="/orgs/{organization_id}/workflows", tags=["workflows"])


def workflow_service(
    workflows: Annotated[WorkflowRepository, Depends(workflow_repository_dependency)],
    members: Annotated[OrganizationMemberRepository, Depends(organization_member_repository_dependency)],
) -> WorkflowService:
    return WorkflowService(workflows, members)


def workflow_ai_service() -> WorkflowAIService:
    return WorkflowAIService()


@router.post("", response_model=WorkflowRead, status_code=status.HTTP_201_CREATED)
async def create_workflow(
    organization_id: str,
    payload: WorkflowCreate,
    current_user: Annotated[User, Depends(current_user_dependency)],
    service: Annotated[WorkflowService, Depends(workflow_service)],
) -> WorkflowRead:
    try:
        return await service.create(organization_id, payload, current_user)
    except OrganizationAccessDeniedError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Organization access denied") from exc


@router.get("", response_model=list[WorkflowRead])
async def list_workflows(
    organization_id: str,
    current_user: Annotated[User, Depends(current_user_dependency)],
    service: Annotated[WorkflowService, Depends(workflow_service)],
) -> list[WorkflowRead]:
    try:
        return await service.list_for_organization(organization_id, current_user)
    except OrganizationAccessDeniedError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Organization access denied") from exc


@router.get("/{workflow_id}", response_model=WorkflowRead)
async def get_workflow(
    organization_id: str,
    workflow_id: str,
    current_user: Annotated[User, Depends(current_user_dependency)],
    service: Annotated[WorkflowService, Depends(workflow_service)],
) -> WorkflowRead:
    try:
        return await service.get(organization_id, workflow_id, current_user)
    except OrganizationAccessDeniedError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Organization access denied") from exc
    except WorkflowNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found") from exc


@router.post("/{workflow_id}/validate", response_model=WorkflowValidationResult)
async def validate_workflow(
    organization_id: str,
    workflow_id: str,
    current_user: Annotated[User, Depends(current_user_dependency)],
    service: Annotated[WorkflowService, Depends(workflow_service)],
) -> WorkflowValidationResult:
    try:
        return await service.validate(organization_id, workflow_id, current_user)
    except OrganizationAccessDeniedError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Organization access denied") from exc
    except WorkflowNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found") from exc


@router.post("/{workflow_id}/validate-draft", response_model=WorkflowValidationResult)
async def validate_workflow_draft(
    organization_id: str,
    workflow_id: str,
    payload: WorkflowUpdate,
    current_user: Annotated[User, Depends(current_user_dependency)],
    service: Annotated[WorkflowService, Depends(workflow_service)],
) -> WorkflowValidationResult:
    try:
        return await service.validate_draft(organization_id, workflow_id, payload, current_user)
    except OrganizationAccessDeniedError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Organization access denied") from exc
    except WorkflowNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found") from exc
    except WorkflowRevisionConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Workflow revision conflict") from exc


@router.post("/{workflow_id}/ai/generate-graph", response_model=WorkflowAIGenerateResponse)
async def generate_workflow_graph(
    organization_id: str,
    workflow_id: str,
    payload: WorkflowAIGenerateRequest,
    current_user: Annotated[User, Depends(current_user_dependency)],
    service: Annotated[WorkflowService, Depends(workflow_service)],
    ai_service: Annotated[WorkflowAIService, Depends(workflow_ai_service)],
) -> WorkflowAIGenerateResponse:
    try:
        return await service.generate_ai_graph(
            organization_id,
            workflow_id,
            payload.prompt,
            payload.use_current_graph,
            current_user,
            ai_service,
        )
    except OrganizationAccessDeniedError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Organization access denied") from exc
    except WorkflowNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found") from exc
    except WorkflowRevisionConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Workflow revision conflict") from exc
    except AIConfigurationError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="AI is not set up.") from exc
    except AIGenerationError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI could not generate a workflow graph",
        ) from exc


@router.get("/{workflow_id}/ai/status", response_model=WorkflowAIStatusResponse)
async def workflow_ai_status(
    organization_id: str,
    workflow_id: str,
    current_user: Annotated[User, Depends(current_user_dependency)],
    service: Annotated[WorkflowService, Depends(workflow_service)],
) -> WorkflowAIStatusResponse:
    try:
        await service.get(organization_id, workflow_id, current_user)
    except OrganizationAccessDeniedError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Organization access denied") from exc
    except WorkflowNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found") from exc

    return WorkflowAIStatusResponse(configured=bool(settings.openai_api_key))


@router.post("/{workflow_id}/ai/analyze-graph", response_model=WorkflowAIAnalyzeResponse)
async def analyze_workflow_graph(
    organization_id: str,
    workflow_id: str,
    payload: WorkflowAIAnalyzeRequest,
    current_user: Annotated[User, Depends(current_user_dependency)],
    service: Annotated[WorkflowService, Depends(workflow_service)],
    ai_service: Annotated[WorkflowAIService, Depends(workflow_ai_service)],
) -> WorkflowAIAnalyzeResponse:
    try:
        return await service.analyze_ai_graph(
            organization_id,
            workflow_id,
            WorkflowUpdate(name="Analysis draft", nodes=payload.nodes, edges=payload.edges, revision=payload.revision),
            current_user,
            ai_service,
        )
    except OrganizationAccessDeniedError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Organization access denied") from exc
    except WorkflowNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found") from exc
    except WorkflowRevisionConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Workflow revision conflict") from exc
    except AIConfigurationError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="AI is not set up.") from exc
    except AIGenerationError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI could not analyze the workflow graph",
        ) from exc


@router.post("/{workflow_id}/activate", response_model=WorkflowRead)
async def activate_workflow(
    organization_id: str,
    workflow_id: str,
    current_user: Annotated[User, Depends(current_user_dependency)],
    service: Annotated[WorkflowService, Depends(workflow_service)],
) -> WorkflowRead:
    try:
        return await service.activate(organization_id, workflow_id, current_user)
    except OrganizationAccessDeniedError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Organization access denied") from exc
    except WorkflowNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found") from exc
    except WorkflowRevisionConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Workflow revision conflict") from exc
    except WorkflowValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=exc.result.model_dump(),
        ) from exc


@router.post("/{workflow_id}/deactivate", response_model=WorkflowRead)
async def deactivate_workflow(
    organization_id: str,
    workflow_id: str,
    current_user: Annotated[User, Depends(current_user_dependency)],
    service: Annotated[WorkflowService, Depends(workflow_service)],
) -> WorkflowRead:
    try:
        return await service.deactivate(organization_id, workflow_id, current_user)
    except OrganizationAccessDeniedError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Organization access denied") from exc
    except WorkflowNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found") from exc
    except WorkflowRevisionConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Workflow revision conflict") from exc


@router.put("/{workflow_id}", response_model=WorkflowRead)
async def update_workflow(
    organization_id: str,
    workflow_id: str,
    payload: WorkflowUpdate,
    current_user: Annotated[User, Depends(current_user_dependency)],
    service: Annotated[WorkflowService, Depends(workflow_service)],
) -> WorkflowRead:
    try:
        return await service.update(organization_id, workflow_id, payload, current_user)
    except OrganizationAccessDeniedError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Organization access denied") from exc
    except WorkflowNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found") from exc
    except WorkflowRevisionConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Workflow revision conflict") from exc


@router.delete("/{workflow_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workflow(
    organization_id: str,
    workflow_id: str,
    current_user: Annotated[User, Depends(current_user_dependency)],
    service: Annotated[WorkflowService, Depends(workflow_service)],
) -> Response:
    try:
        await service.delete(organization_id, workflow_id, current_user)
    except OrganizationAccessDeniedError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Organization access denied") from exc
    except WorkflowNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found") from exc
    except WorkflowRevisionConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Workflow revision conflict") from exc

    return Response(status_code=status.HTTP_204_NO_CONTENT)
