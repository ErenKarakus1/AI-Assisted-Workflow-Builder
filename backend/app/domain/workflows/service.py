from datetime import UTC, datetime

from app.domain.orgs.repository import OrganizationMemberRepository
from app.domain.orgs.service import OrganizationAccessDeniedError
from app.domain.workflows.repository import WorkflowRepository
from app.domain.workflows.validation import WorkflowValidator
from app.models.user import User
from app.models.workflow import Workflow, WorkflowStatus
from app.schemas.workflow import WorkflowCreate, WorkflowRead, WorkflowUpdate, WorkflowValidationResult


class WorkflowNotFoundError(Exception):
    pass


class WorkflowRevisionConflictError(Exception):
    pass


class WorkflowValidationError(Exception):
    def __init__(self, result: WorkflowValidationResult) -> None:
        self.result = result


class WorkflowService:
    def __init__(
        self,
        workflows: WorkflowRepository,
        members: OrganizationMemberRepository,
    ) -> None:
        self.workflows = workflows
        self.members = members

    async def create(
        self,
        organization_id: str,
        payload: WorkflowCreate,
        user: User,
    ) -> WorkflowRead:
        await self._ensure_membership(organization_id, user)
        workflow = Workflow(
            organization_id=organization_id,
            name=payload.name.strip(),
            nodes=payload.nodes,
            edges=payload.edges,
            created_by_user_id=user.id,
        )
        return self._read(await self.workflows.create(workflow))

    async def list_for_organization(self, organization_id: str, user: User) -> list[WorkflowRead]:
        await self._ensure_membership(organization_id, user)
        workflows = await self.workflows.list_by_organization(organization_id)
        return [self._read(workflow) for workflow in workflows]

    async def get(self, organization_id: str, workflow_id: str, user: User) -> WorkflowRead:
        workflow = await self._get_for_organization(organization_id, workflow_id, user)
        return self._read(workflow)

    async def update(
        self,
        organization_id: str,
        workflow_id: str,
        payload: WorkflowUpdate,
        user: User,
    ) -> WorkflowRead:
        workflow = await self._get_for_organization(organization_id, workflow_id, user)
        if workflow.revision != payload.revision:
            raise WorkflowRevisionConflictError
        if workflow.status != WorkflowStatus.DRAFT:
            raise WorkflowRevisionConflictError

        workflow.name = payload.name.strip()
        workflow.nodes = payload.nodes
        workflow.edges = payload.edges
        workflow.revision += 1
        workflow.updated_at = datetime.now(UTC)
        return self._read(await self.workflows.update(workflow))

    async def delete(self, organization_id: str, workflow_id: str, user: User) -> None:
        workflow = await self._get_for_organization(organization_id, workflow_id, user)
        if workflow.status != WorkflowStatus.DRAFT:
            raise WorkflowRevisionConflictError
        await self.workflows.delete(workflow.id)

    async def validate(
        self,
        organization_id: str,
        workflow_id: str,
        user: User,
    ) -> WorkflowValidationResult:
        workflow = await self._get_for_organization(organization_id, workflow_id, user)
        return WorkflowValidator().validate(workflow)

    async def validate_draft(
        self,
        organization_id: str,
        workflow_id: str,
        payload: WorkflowUpdate,
        user: User,
    ) -> WorkflowValidationResult:
        workflow = await self._get_for_organization(organization_id, workflow_id, user)
        if workflow.revision != payload.revision:
            raise WorkflowRevisionConflictError

        draft = workflow.model_copy(
            update={
                "name": payload.name.strip(),
                "nodes": payload.nodes,
                "edges": payload.edges,
            }
        )
        return WorkflowValidator().validate(draft)

    async def activate(self, organization_id: str, workflow_id: str, user: User) -> WorkflowRead:
        workflow = await self._get_for_organization(organization_id, workflow_id, user)
        if workflow.status != WorkflowStatus.DRAFT:
            raise WorkflowRevisionConflictError

        validation_result = WorkflowValidator().validate(workflow)
        if not validation_result.is_valid:
            raise WorkflowValidationError(validation_result)

        workflow.status = WorkflowStatus.ACTIVE
        workflow.revision += 1
        workflow.updated_at = datetime.now(UTC)
        return self._read(await self.workflows.update(workflow))

    async def deactivate(self, organization_id: str, workflow_id: str, user: User) -> WorkflowRead:
        workflow = await self._get_for_organization(organization_id, workflow_id, user)
        if workflow.status != WorkflowStatus.ACTIVE:
            raise WorkflowRevisionConflictError

        workflow.status = WorkflowStatus.DRAFT
        workflow.revision += 1
        workflow.updated_at = datetime.now(UTC)
        return self._read(await self.workflows.update(workflow))

    async def _ensure_membership(self, organization_id: str, user: User) -> None:
        membership = await self.members.get_by_user_and_org(user.id, organization_id)
        if not membership:
            raise OrganizationAccessDeniedError

    async def _get_for_organization(
        self,
        organization_id: str,
        workflow_id: str,
        user: User,
    ) -> Workflow:
        await self._ensure_membership(organization_id, user)
        workflow = await self.workflows.get_by_id(workflow_id)
        if not workflow or workflow.organization_id != organization_id:
            raise WorkflowNotFoundError
        return workflow

    def _read(self, workflow: Workflow) -> WorkflowRead:
        return WorkflowRead(
            id=workflow.id,
            organization_id=workflow.organization_id,
            name=workflow.name,
            status=workflow.status,
            nodes=workflow.nodes,
            edges=workflow.edges,
            revision=workflow.revision,
        )
