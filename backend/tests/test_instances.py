import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import (
    instance_event_repository_dependency,
    organization_member_repository_dependency,
    organization_repository_dependency,
    scheduled_job_repository_dependency,
    task_repository_dependency,
    user_repository_dependency,
    workflow_instance_repository_dependency,
    workflow_repository_dependency,
)
from app.domain.auth.repository import UserRepository
from app.domain.instances.repository import InstanceEventRepository, WorkflowInstanceRepository
from app.domain.orgs.repository import OrganizationMemberRepository, OrganizationRepository
from app.domain.scheduling.repository import ScheduledJobRepository
from app.domain.tasks.repository import TaskRepository
from app.domain.workflows.repository import WorkflowRepository
from app.main import create_app
from tests.fakes import (
    InMemoryInstanceEventRepository,
    InMemoryOrganizationMemberRepository,
    InMemoryOrganizationRepository,
    InMemoryScheduledJobRepository,
    InMemoryTaskRepository,
    InMemoryUserRepository,
    InMemoryWorkflowInstanceRepository,
    InMemoryWorkflowRepository,
)


@pytest.fixture
def client() -> TestClient:
    app = create_app()
    user_repository = InMemoryUserRepository()
    organization_repository = InMemoryOrganizationRepository()
    member_repository = InMemoryOrganizationMemberRepository()
    workflow_repository = InMemoryWorkflowRepository()
    instance_repository = InMemoryWorkflowInstanceRepository()
    event_repository = InMemoryInstanceEventRepository()
    task_repository = InMemoryTaskRepository()
    job_repository = InMemoryScheduledJobRepository()

    async def override_user_repository() -> UserRepository:
        return user_repository

    async def override_organization_repository() -> OrganizationRepository:
        return organization_repository

    async def override_member_repository() -> OrganizationMemberRepository:
        return member_repository

    async def override_workflow_repository() -> WorkflowRepository:
        return workflow_repository

    async def override_instance_repository() -> WorkflowInstanceRepository:
        return instance_repository

    async def override_event_repository() -> InstanceEventRepository:
        return event_repository

    async def override_task_repository() -> TaskRepository:
        return task_repository

    async def override_job_repository() -> ScheduledJobRepository:
        return job_repository

    app.dependency_overrides[user_repository_dependency] = override_user_repository
    app.dependency_overrides[organization_repository_dependency] = override_organization_repository
    app.dependency_overrides[organization_member_repository_dependency] = override_member_repository
    app.dependency_overrides[workflow_repository_dependency] = override_workflow_repository
    app.dependency_overrides[workflow_instance_repository_dependency] = override_instance_repository
    app.dependency_overrides[instance_event_repository_dependency] = override_event_repository
    app.dependency_overrides[task_repository_dependency] = override_task_repository
    app.dependency_overrides[scheduled_job_repository_dependency] = override_job_repository
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


def simple_workflow_payload() -> dict:
    return {
        "name": "Simple Flow",
        "nodes": [
            {"id": "start-1", "type": "start", "position": {}, "data": {}},
            {"id": "end-1", "type": "end", "position": {}, "data": {"result": "approved"}},
        ],
        "edges": [
            {"id": "edge-1", "source": "start-1", "target": "end-1", "label": None, "data": {}}
        ],
    }


def condition_workflow_payload() -> dict:
    return {
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
                        "operator": "greater_than_or_equal",
                        "value": 1000,
                    }
                },
            },
            {"id": "high-end", "type": "end", "position": {}, "data": {"result": "high"}},
            {"id": "low-end", "type": "end", "position": {}, "data": {"result": "low"}},
        ],
        "edges": [
            {"id": "edge-1", "source": "start-1", "target": "condition-1", "label": None, "data": {}},
            {"id": "edge-2", "source": "condition-1", "target": "high-end", "label": "true", "data": {}},
            {"id": "edge-3", "source": "condition-1", "target": "low-end", "label": "false", "data": {}},
        ],
    }


def create_and_activate_workflow(client: TestClient, token: str, org_id: str, payload: dict) -> str:
    create_response = client.post(
        f"/api/orgs/{org_id}/workflows",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    workflow_id = create_response.json()["id"]
    activate_response = client.post(
        f"/api/orgs/{org_id}/workflows/{workflow_id}/activate",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert activate_response.status_code == 200
    return workflow_id


def test_start_simple_workflow_instance_completes(client: TestClient) -> None:
    token, org_id = register_login_create_org(client, "owner@example.com", "Owner Org")
    workflow_id = create_and_activate_workflow(client, token, org_id, simple_workflow_payload())

    response = client.post(
        f"/api/orgs/{org_id}/workflows/{workflow_id}/instances",
        json={"input": {"amount": 250}},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 201
    assert response.json()["status"] == "completed"
    assert response.json()["context"]["result"] == "approved"
    assert response.json()["input"] == {"amount": 250}


def test_member_can_start_active_workflow_instance(client: TestClient) -> None:
    owner_token, org_id = register_login_create_org(client, "owner@example.com", "Owner Org")
    member_token = register_and_login(client, "member@example.com")
    workflow_id = create_and_activate_workflow(client, owner_token, org_id, simple_workflow_payload())
    client.post(
        f"/api/orgs/{org_id}/members",
        json={"email": "member@example.com", "role": "member"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )

    response = client.post(
        f"/api/orgs/{org_id}/workflows/{workflow_id}/instances",
        json={"input": {"amount": 250}},
        headers={"Authorization": f"Bearer {member_token}"},
    )

    assert response.status_code == 201
    assert response.json()["status"] == "completed"


def test_condition_workflow_takes_true_branch(client: TestClient) -> None:
    token, org_id = register_login_create_org(client, "owner@example.com", "Owner Org")
    workflow_id = create_and_activate_workflow(client, token, org_id, condition_workflow_payload())

    response = client.post(
        f"/api/orgs/{org_id}/workflows/{workflow_id}/instances",
        json={"input": {"amount": 1500}},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 201
    assert response.json()["status"] == "completed"
    assert response.json()["context"]["condition_condition-1"] is True
    assert response.json()["context"]["result"] == "high"


def test_condition_missing_input_takes_false_branch(client: TestClient) -> None:
    token, org_id = register_login_create_org(client, "owner@example.com", "Owner Org")
    workflow_id = create_and_activate_workflow(client, token, org_id, condition_workflow_payload())

    response = client.post(
        f"/api/orgs/{org_id}/workflows/{workflow_id}/instances",
        json={"input": {}},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 201
    assert response.json()["status"] == "completed"
    assert response.json()["context"]["condition_condition-1"] is False
    assert response.json()["context"]["result"] == "low"


def test_instance_events_are_append_only_timeline(client: TestClient) -> None:
    token, org_id = register_login_create_org(client, "owner@example.com", "Owner Org")
    workflow_id = create_and_activate_workflow(client, token, org_id, condition_workflow_payload())
    instance_response = client.post(
        f"/api/orgs/{org_id}/workflows/{workflow_id}/instances",
        json={"input": {"amount": 50}},
        headers={"Authorization": f"Bearer {token}"},
    )

    response = client.get(
        f"/api/orgs/{org_id}/instances/{instance_response.json()['id']}/events",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert [event["type"] for event in response.json()] == [
        "instance_started",
        "node_entered",
        "node_entered",
        "condition_evaluated",
        "node_entered",
        "instance_completed",
    ]
    assert response.json()[3]["data"] == {"result": False, "branch": "false"}


def test_list_workflow_instances(client: TestClient) -> None:
    token, org_id = register_login_create_org(client, "owner@example.com", "Owner Org")
    workflow_id = create_and_activate_workflow(client, token, org_id, simple_workflow_payload())
    client.post(
        f"/api/orgs/{org_id}/workflows/{workflow_id}/instances",
        json={"input": {"amount": 1}},
        headers={"Authorization": f"Bearer {token}"},
    )
    client.post(
        f"/api/orgs/{org_id}/workflows/{workflow_id}/instances",
        json={"input": {"amount": 2}},
        headers={"Authorization": f"Bearer {token}"},
    )

    response = client.get(
        f"/api/orgs/{org_id}/workflows/{workflow_id}/instances",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert len(response.json()) == 2
    assert {instance["input"]["amount"] for instance in response.json()} == {1, 2}


def test_cannot_start_draft_workflow(client: TestClient) -> None:
    token, org_id = register_login_create_org(client, "owner@example.com", "Owner Org")
    workflow_response = client.post(
        f"/api/orgs/{org_id}/workflows",
        json=simple_workflow_payload(),
        headers={"Authorization": f"Bearer {token}"},
    )

    response = client.post(
        f"/api/orgs/{org_id}/workflows/{workflow_response.json()['id']}/instances",
        json={"input": {}},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 409


def test_get_instance_requires_org_membership(client: TestClient) -> None:
    owner_token, owner_org_id = register_login_create_org(client, "owner@example.com", "Owner Org")
    other_token, _ = register_login_create_org(client, "other@example.com", "Other Org")
    workflow_id = create_and_activate_workflow(
        client,
        owner_token,
        owner_org_id,
        simple_workflow_payload(),
    )
    instance_response = client.post(
        f"/api/orgs/{owner_org_id}/workflows/{workflow_id}/instances",
        json={"input": {}},
        headers={"Authorization": f"Bearer {owner_token}"},
    )

    response = client.get(
        f"/api/orgs/{owner_org_id}/instances/{instance_response.json()['id']}",
        headers={"Authorization": f"Bearer {other_token}"},
    )

    assert response.status_code == 403
