import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import (
    organization_member_repository_dependency,
    organization_repository_dependency,
    user_repository_dependency,
    workflow_repository_dependency,
)
from app.api.routes.workflows import workflow_ai_service
from app.domain.auth.repository import UserRepository
from app.domain.orgs.repository import OrganizationMemberRepository, OrganizationRepository
from app.domain.workflows.repository import WorkflowRepository
from app.main import create_app
from app.models.workflow import Workflow, WorkflowEdge, WorkflowNode
from app.schemas.workflow import WorkflowAIGenerateResponse, WorkflowValidationResult
from tests.fakes import (
    InMemoryOrganizationMemberRepository,
    InMemoryOrganizationRepository,
    InMemoryUserRepository,
    InMemoryWorkflowRepository,
)


class FakeWorkflowAIService:
    async def generate_graph(self, workflow: Workflow, prompt: str) -> WorkflowAIGenerateResponse:
        nodes = [
            WorkflowNode(id="start-1", type="start", position={"x": 0, "y": 0}, data={"label": "Start"}),
            WorkflowNode(id="end-1", type="end", position={"x": 300, "y": 0}, data={"label": "End"}),
        ]
        edges = [
            WorkflowEdge(id="edge-1", source="start-1", target="end-1", label=None, data={}),
        ]
        return WorkflowAIGenerateResponse(
            nodes=nodes,
            edges=edges,
            explanation=f"Generated from: {prompt}",
            validation=WorkflowValidationResult(is_valid=True),
        )


@pytest.fixture
def client() -> TestClient:
    app = create_app()
    user_repository = InMemoryUserRepository()
    organization_repository = InMemoryOrganizationRepository()
    member_repository = InMemoryOrganizationMemberRepository()
    workflow_repository = InMemoryWorkflowRepository()

    async def override_user_repository() -> UserRepository:
        return user_repository

    async def override_organization_repository() -> OrganizationRepository:
        return organization_repository

    async def override_member_repository() -> OrganizationMemberRepository:
        return member_repository

    async def override_workflow_repository() -> WorkflowRepository:
        return workflow_repository

    app.dependency_overrides[user_repository_dependency] = override_user_repository
    app.dependency_overrides[organization_repository_dependency] = override_organization_repository
    app.dependency_overrides[organization_member_repository_dependency] = override_member_repository
    app.dependency_overrides[workflow_repository_dependency] = override_workflow_repository
    app.dependency_overrides[workflow_ai_service] = lambda: FakeWorkflowAIService()
    return TestClient(app)


def register_login_create_org(client: TestClient, email: str, org_name: str) -> tuple[str, str]:
    client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": "correct-horse-battery",
            "full_name": "Workflow User",
        },
    )
    login_response = client.post(
        "/api/auth/login",
        json={"email": email, "password": "correct-horse-battery"},
    )
    token = login_response.json()["access_token"]
    org_response = client.post(
        "/api/orgs",
        json={"name": org_name},
        headers={"Authorization": f"Bearer {token}"},
    )
    return token, org_response.json()["id"]


def register_and_login(client: TestClient, email: str) -> str:
    client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": "correct-horse-battery",
            "full_name": "Workflow User",
        },
    )
    login_response = client.post(
        "/api/auth/login",
        json={"email": email, "password": "correct-horse-battery"},
    )
    return login_response.json()["access_token"]


def workflow_payload(name: str = "Employee Onboarding") -> dict:
    return {
        "name": name,
        "nodes": [
            {"id": "start-1", "type": "start", "position": {"x": 0, "y": 0}, "data": {}},
            {"id": "end-1", "type": "end", "position": {"x": 300, "y": 0}, "data": {}},
        ],
        "edges": [
            {"id": "edge-1", "source": "start-1", "target": "end-1", "label": None, "data": {}}
        ],
    }


def approval_workflow_payload(name: str = "Approval Flow") -> dict:
    return {
        "name": name,
        "nodes": [
            {"id": "start-1", "type": "start", "position": {"x": 0, "y": 0}, "data": {}},
            {
                "id": "approval-1",
                "type": "approval",
                "position": {"x": 160, "y": 0},
                "data": {"assigned_role": "member"},
            },
            {"id": "approved-end", "type": "end", "position": {"x": 320, "y": -80}, "data": {}},
            {"id": "rejected-end", "type": "end", "position": {"x": 320, "y": 80}, "data": {}},
        ],
        "edges": [
            {
                "id": "edge-start-approval",
                "source": "start-1",
                "target": "approval-1",
                "label": None,
                "data": {},
            },
            {
                "id": "edge-approve",
                "source": "approval-1",
                "target": "approved-end",
                "label": "approve",
                "data": {},
            },
            {
                "id": "edge-reject",
                "source": "approval-1",
                "target": "rejected-end",
                "label": "reject",
                "data": {},
            },
        ],
    }


def test_create_and_get_workflow(client: TestClient) -> None:
    token, org_id = register_login_create_org(client, "owner@example.com", "Owner Org")

    create_response = client.post(
        f"/api/orgs/{org_id}/workflows",
        json=workflow_payload(),
        headers={"Authorization": f"Bearer {token}"},
    )

    assert create_response.status_code == 201
    workflow = create_response.json()
    assert workflow["name"] == "Employee Onboarding"
    assert workflow["status"] == "draft"
    assert workflow["revision"] == 1

    get_response = client.get(
        f"/api/orgs/{org_id}/workflows/{workflow['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert get_response.status_code == 200
    assert get_response.json()["id"] == workflow["id"]


def test_list_workflows_is_scoped_to_organization(client: TestClient) -> None:
    token, first_org_id = register_login_create_org(client, "owner@example.com", "First Org")
    _, second_org_id = register_login_create_org(client, "other@example.com", "Second Org")

    client.post(
        f"/api/orgs/{first_org_id}/workflows",
        json=workflow_payload("First Workflow"),
        headers={"Authorization": f"Bearer {token}"},
    )

    response = client.get(
        f"/api/orgs/{second_org_id}/workflows",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403


def test_update_workflow_increments_revision(client: TestClient) -> None:
    token, org_id = register_login_create_org(client, "owner@example.com", "Owner Org")
    create_response = client.post(
        f"/api/orgs/{org_id}/workflows",
        json=workflow_payload(),
        headers={"Authorization": f"Bearer {token}"},
    )
    workflow = create_response.json()

    update_payload = workflow_payload("Updated Workflow")
    update_payload["revision"] = workflow["revision"]
    response = client.put(
        f"/api/orgs/{org_id}/workflows/{workflow['id']}",
        json=update_payload,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Updated Workflow"
    assert response.json()["revision"] == 2


def test_update_with_stale_revision_returns_conflict(client: TestClient) -> None:
    token, org_id = register_login_create_org(client, "owner@example.com", "Owner Org")
    create_response = client.post(
        f"/api/orgs/{org_id}/workflows",
        json=workflow_payload(),
        headers={"Authorization": f"Bearer {token}"},
    )
    workflow = create_response.json()
    update_payload = workflow_payload("Updated Workflow")
    update_payload["revision"] = workflow["revision"]
    client.put(
        f"/api/orgs/{org_id}/workflows/{workflow['id']}",
        json=update_payload,
        headers={"Authorization": f"Bearer {token}"},
    )

    stale_payload = workflow_payload("Stale Update")
    stale_payload["revision"] = workflow["revision"]
    response = client.put(
        f"/api/orgs/{org_id}/workflows/{workflow['id']}",
        json=stale_payload,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 409


def test_delete_workflow(client: TestClient) -> None:
    token, org_id = register_login_create_org(client, "owner@example.com", "Owner Org")
    create_response = client.post(
        f"/api/orgs/{org_id}/workflows",
        json=workflow_payload(),
        headers={"Authorization": f"Bearer {token}"},
    )
    workflow_id = create_response.json()["id"]

    delete_response = client.delete(
        f"/api/orgs/{org_id}/workflows/{workflow_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    get_response = client.get(
        f"/api/orgs/{org_id}/workflows/{workflow_id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert delete_response.status_code == 204
    assert get_response.status_code == 404


def test_validate_valid_workflow(client: TestClient) -> None:
    token, org_id = register_login_create_org(client, "owner@example.com", "Owner Org")
    create_response = client.post(
        f"/api/orgs/{org_id}/workflows",
        json=workflow_payload(),
        headers={"Authorization": f"Bearer {token}"},
    )

    response = client.post(
        f"/api/orgs/{org_id}/workflows/{create_response.json()['id']}/validate",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json() == {"is_valid": True, "errors": [], "warnings": []}


def test_validate_reports_unreachable_node(client: TestClient) -> None:
    token, org_id = register_login_create_org(client, "owner@example.com", "Owner Org")
    payload = workflow_payload()
    payload["nodes"].append(
        {"id": "orphan-end", "type": "end", "position": {"x": 500, "y": 0}, "data": {}}
    )
    create_response = client.post(
        f"/api/orgs/{org_id}/workflows",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )

    response = client.post(
        f"/api/orgs/{org_id}/workflows/{create_response.json()['id']}/validate",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["is_valid"] is False
    assert response.json()["errors"][0]["code"] == "unreachable_node"


def test_condition_requires_true_and_false_branches(client: TestClient) -> None:
    token, org_id = register_login_create_org(client, "owner@example.com", "Owner Org")
    payload = {
        "name": "Conditional Flow",
        "nodes": [
            {"id": "start-1", "type": "start", "position": {}, "data": {}},
            {
                "id": "condition-1",
                "type": "condition",
                "position": {},
                "data": {
                    "condition": {
                        "field": "input.amount",
                        "operator": "greater_than",
                        "value": 100,
                    }
                },
            },
            {"id": "end-1", "type": "end", "position": {}, "data": {}},
        ],
        "edges": [
            {"id": "edge-1", "source": "start-1", "target": "condition-1", "label": None, "data": {}},
            {"id": "edge-2", "source": "condition-1", "target": "end-1", "label": "true", "data": {}},
        ],
    }
    create_response = client.post(
        f"/api/orgs/{org_id}/workflows",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )

    response = client.post(
        f"/api/orgs/{org_id}/workflows/{create_response.json()['id']}/validate",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["is_valid"] is False
    assert any(error["code"] == "condition_missing_branch" for error in response.json()["errors"])


def test_validation_rejects_invalid_node_configs(client: TestClient) -> None:
    token, org_id = register_login_create_org(client, "owner@example.com", "Owner Org")
    payload = {
        "name": "Bad Config Flow",
        "nodes": [
            {"id": "start-1", "type": "start", "position": {}, "data": {}},
            {"id": "delay-1", "type": "delay", "position": {}, "data": {"seconds": -1}},
            {"id": "approval-1", "type": "approval", "position": {}, "data": {}},
            {"id": "condition-1", "type": "condition", "position": {}, "data": {"condition": {"field": ""}}},
            {"id": "end-1", "type": "end", "position": {}, "data": {}},
            {"id": "end-2", "type": "end", "position": {}, "data": {}},
            {"id": "end-3", "type": "end", "position": {}, "data": {}},
        ],
        "edges": [
            {"id": "edge-1", "source": "start-1", "target": "delay-1", "label": None, "data": {}},
            {"id": "edge-2", "source": "delay-1", "target": "approval-1", "label": None, "data": {}},
            {"id": "edge-3", "source": "approval-1", "target": "end-1", "label": "approve", "data": {}},
            {"id": "edge-4", "source": "approval-1", "target": "condition-1", "label": "reject", "data": {}},
            {"id": "edge-5", "source": "condition-1", "target": "end-2", "label": "true", "data": {}},
            {"id": "edge-6", "source": "condition-1", "target": "end-3", "label": "false", "data": {}},
        ],
    }
    create_response = client.post(
        f"/api/orgs/{org_id}/workflows",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )

    response = client.post(
        f"/api/orgs/{org_id}/workflows/{create_response.json()['id']}/validate",
        headers={"Authorization": f"Bearer {token}"},
    )

    codes = {error["code"] for error in response.json()["errors"]}
    assert response.status_code == 200
    assert response.json()["is_valid"] is False
    assert "delay_seconds_invalid" in codes
    assert "approval_assignment_invalid" in codes
    assert "condition_field_missing" in codes
    assert "condition_operator_unsupported" in codes


def test_activate_valid_workflow(client: TestClient) -> None:
    token, org_id = register_login_create_org(client, "owner@example.com", "Owner Org")
    create_response = client.post(
        f"/api/orgs/{org_id}/workflows",
        json=approval_workflow_payload(),
        headers={"Authorization": f"Bearer {token}"},
    )

    response = client.post(
        f"/api/orgs/{org_id}/workflows/{create_response.json()['id']}/activate",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "active"
    assert response.json()["revision"] == 2


def test_activate_invalid_workflow_returns_validation_errors(client: TestClient) -> None:
    token, org_id = register_login_create_org(client, "owner@example.com", "Owner Org")
    create_response = client.post(
        f"/api/orgs/{org_id}/workflows",
        json={
            "name": "Invalid Flow",
            "nodes": [{"id": "start-1", "type": "start", "position": {}, "data": {}}],
            "edges": [],
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    response = client.post(
        f"/api/orgs/{org_id}/workflows/{create_response.json()['id']}/activate",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 422
    assert response.json()["detail"]["is_valid"] is False


def test_active_workflow_cannot_be_updated(client: TestClient) -> None:
    token, org_id = register_login_create_org(client, "owner@example.com", "Owner Org")
    create_response = client.post(
        f"/api/orgs/{org_id}/workflows",
        json=approval_workflow_payload(),
        headers={"Authorization": f"Bearer {token}"},
    )
    workflow_id = create_response.json()["id"]
    activated_response = client.post(
        f"/api/orgs/{org_id}/workflows/{workflow_id}/activate",
        headers={"Authorization": f"Bearer {token}"},
    )
    update_payload = approval_workflow_payload("Edited Active Flow")
    update_payload["revision"] = activated_response.json()["revision"]

    response = client.put(
        f"/api/orgs/{org_id}/workflows/{workflow_id}",
        json=update_payload,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 409


def test_deactivate_active_workflow_returns_to_draft(client: TestClient) -> None:
    token, org_id = register_login_create_org(client, "owner@example.com", "Owner Org")
    create_response = client.post(
        f"/api/orgs/{org_id}/workflows",
        json=approval_workflow_payload(),
        headers={"Authorization": f"Bearer {token}"},
    )
    workflow_id = create_response.json()["id"]
    client.post(
        f"/api/orgs/{org_id}/workflows/{workflow_id}/activate",
        headers={"Authorization": f"Bearer {token}"},
    )

    response = client.post(
        f"/api/orgs/{org_id}/workflows/{workflow_id}/deactivate",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "draft"
    assert response.json()["revision"] == 3


def test_validate_draft_uses_unsaved_graph(client: TestClient) -> None:
    token, org_id = register_login_create_org(client, "owner@example.com", "Owner Org")
    create_response = client.post(
        f"/api/orgs/{org_id}/workflows",
        json=workflow_payload(),
        headers={"Authorization": f"Bearer {token}"},
    )
    workflow = create_response.json()
    payload = workflow_payload("Unsaved Bad Graph")
    payload["revision"] = workflow["revision"]
    payload["edges"] = []

    response = client.post(
        f"/api/orgs/{org_id}/workflows/{workflow['id']}/validate-draft",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["is_valid"] is False
    assert any(error["code"] == "start_outgoing_count" for error in response.json()["errors"])


def test_generate_workflow_graph_with_ai(client: TestClient) -> None:
    token, org_id = register_login_create_org(client, "owner@example.com", "Owner Org")
    create_response = client.post(
        f"/api/orgs/{org_id}/workflows",
        json=workflow_payload(),
        headers={"Authorization": f"Bearer {token}"},
    )
    workflow = create_response.json()

    response = client.post(
        f"/api/orgs/{org_id}/workflows/{workflow['id']}/ai/generate-graph",
        json={"prompt": "Create a simple workflow that starts and then completes."},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["nodes"][0]["id"] == "start-1"
    assert body["edges"][0]["source"] == "start-1"
    assert body["validation"]["is_valid"] is True
    assert body["explanation"].startswith("Generated from:")


def test_member_can_view_but_not_create_workflow(client: TestClient) -> None:
    owner_token, org_id = register_login_create_org(client, "owner@example.com", "Owner Org")
    member_token = register_and_login(client, "member@example.com")
    client.post(
        f"/api/orgs/{org_id}/members",
        json={"email": "member@example.com", "role": "member"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    create_response = client.post(
        f"/api/orgs/{org_id}/workflows",
        json=workflow_payload(),
        headers={"Authorization": f"Bearer {owner_token}"},
    )

    list_response = client.get(
        f"/api/orgs/{org_id}/workflows",
        headers={"Authorization": f"Bearer {member_token}"},
    )
    denied_response = client.post(
        f"/api/orgs/{org_id}/workflows",
        json=workflow_payload("Member Workflow"),
        headers={"Authorization": f"Bearer {member_token}"},
    )

    assert list_response.status_code == 200
    assert list_response.json()[0]["id"] == create_response.json()["id"]
    assert denied_response.status_code == 403


def test_member_cannot_change_workflow(client: TestClient) -> None:
    owner_token, org_id = register_login_create_org(client, "owner@example.com", "Owner Org")
    member_token = register_and_login(client, "member@example.com")
    client.post(
        f"/api/orgs/{org_id}/members",
        json={"email": "member@example.com", "role": "member"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    create_response = client.post(
        f"/api/orgs/{org_id}/workflows",
        json=workflow_payload(),
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    workflow = create_response.json()
    update_payload = workflow_payload("Member Edit")
    update_payload["revision"] = workflow["revision"]

    update_response = client.put(
        f"/api/orgs/{org_id}/workflows/{workflow['id']}",
        json=update_payload,
        headers={"Authorization": f"Bearer {member_token}"},
    )
    activate_response = client.post(
        f"/api/orgs/{org_id}/workflows/{workflow['id']}/activate",
        headers={"Authorization": f"Bearer {member_token}"},
    )
    delete_response = client.delete(
        f"/api/orgs/{org_id}/workflows/{workflow['id']}",
        headers={"Authorization": f"Bearer {member_token}"},
    )

    assert update_response.status_code == 403
    assert activate_response.status_code == 403
    assert delete_response.status_code == 403
