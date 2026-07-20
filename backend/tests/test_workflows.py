import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import (
    organization_member_repository_dependency,
    organization_repository_dependency,
    user_repository_dependency,
    workflow_repository_dependency,
)
from app.domain.auth.repository import UserRepository
from app.domain.orgs.repository import OrganizationMemberRepository, OrganizationRepository
from app.domain.workflows.repository import WorkflowRepository
from app.main import create_app
from tests.fakes import (
    InMemoryOrganizationMemberRepository,
    InMemoryOrganizationRepository,
    InMemoryUserRepository,
    InMemoryWorkflowRepository,
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

