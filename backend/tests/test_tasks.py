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
    app.state.job_repository = job_repository
    return TestClient(app)


def register_login_create_org(client: TestClient, email: str) -> tuple[str, str, str]:
    register_response = client.post(
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
        json={"name": "Owner Org"},
        headers={"Authorization": f"Bearer {token}"},
    )
    return token, org_response.json()["id"], register_response.json()["id"]


def approval_workflow_payload(assigned_user_id: str | None = None) -> dict:
    data = {}
    if assigned_user_id:
        data["assigned_user_id"] = assigned_user_id
    return {
        "name": "Approval Flow",
        "nodes": [
            {"id": "start-1", "type": "start", "position": {}, "data": {}},
            {"id": "approval-1", "type": "approval", "position": {}, "data": data},
            {"id": "approved-end", "type": "end", "position": {}, "data": {"result": "approved"}},
            {"id": "rejected-end", "type": "end", "position": {}, "data": {"result": "rejected"}},
        ],
        "edges": [
            {"id": "edge-1", "source": "start-1", "target": "approval-1", "label": None, "data": {}},
            {"id": "edge-2", "source": "approval-1", "target": "approved-end", "label": "approve", "data": {}},
            {"id": "edge-3", "source": "approval-1", "target": "rejected-end", "label": "reject", "data": {}},
        ],
    }


def approval_then_delay_workflow_payload(assigned_user_id: str) -> dict:
    return {
        "name": "Approval Delay Flow",
        "nodes": [
            {"id": "start-1", "type": "start", "position": {}, "data": {}},
            {
                "id": "approval-1",
                "type": "approval",
                "position": {},
                "data": {"assigned_user_id": assigned_user_id},
            },
            {"id": "delay-1", "type": "delay", "position": {}, "data": {"seconds": 5}},
            {"id": "rejected-end", "type": "end", "position": {}, "data": {"result": "rejected"}},
            {"id": "done-end", "type": "end", "position": {}, "data": {"result": "done"}},
        ],
        "edges": [
            {"id": "edge-1", "source": "start-1", "target": "approval-1", "label": None, "data": {}},
            {"id": "edge-2", "source": "approval-1", "target": "delay-1", "label": "approve", "data": {}},
            {"id": "edge-3", "source": "approval-1", "target": "rejected-end", "label": "reject", "data": {}},
            {"id": "edge-4", "source": "delay-1", "target": "done-end", "label": None, "data": {}},
        ],
    }


def create_activate_start(client: TestClient, token: str, org_id: str, payload: dict) -> dict:
    workflow_response = client.post(
        f"/api/orgs/{org_id}/workflows",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    workflow_id = workflow_response.json()["id"]
    client.post(
        f"/api/orgs/{org_id}/workflows/{workflow_id}/activate",
        headers={"Authorization": f"Bearer {token}"},
    )
    return client.post(
        f"/api/orgs/{org_id}/workflows/{workflow_id}/instances",
        json={"input": {}},
        headers={"Authorization": f"Bearer {token}"},
    ).json()


def test_approval_node_creates_pending_task_and_waits(client: TestClient) -> None:
    token, org_id, user_id = register_login_create_org(client, "owner@example.com")
    instance = create_activate_start(client, token, org_id, approval_workflow_payload(user_id))

    tasks_response = client.get(f"/api/orgs/{org_id}/tasks", headers={"Authorization": f"Bearer {token}"})

    assert instance["status"] == "waiting"
    assert tasks_response.status_code == 200
    assert tasks_response.json()[0]["status"] == "pending"
    assert tasks_response.json()[0]["assigned_user_id"] == user_id


def test_approve_task_resumes_instance_to_approved_end(client: TestClient) -> None:
    token, org_id, user_id = register_login_create_org(client, "owner@example.com")
    instance = create_activate_start(client, token, org_id, approval_workflow_payload(user_id))
    task = client.get(f"/api/orgs/{org_id}/tasks", headers={"Authorization": f"Bearer {token}"}).json()[0]

    response = client.post(
        f"/api/orgs/{org_id}/tasks/{task['id']}/approve",
        json={"revision": task["revision"]},
        headers={"Authorization": f"Bearer {token}"},
    )
    instance_response = client.get(
        f"/api/orgs/{org_id}/instances/{instance['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "completed"
    assert response.json()["decision"] == "approve"
    assert instance_response.json()["status"] == "completed"
    assert instance_response.json()["context"]["result"] == "approved"


def test_approve_task_persists_delay_job_when_next_node_is_delay(client: TestClient) -> None:
    token, org_id, user_id = register_login_create_org(client, "owner@example.com")
    create_activate_start(client, token, org_id, approval_then_delay_workflow_payload(user_id))
    task = client.get(f"/api/orgs/{org_id}/tasks", headers={"Authorization": f"Bearer {token}"}).json()[0]

    response = client.post(
        f"/api/orgs/{org_id}/tasks/{task['id']}/approve",
        json={"revision": task["revision"]},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert len(client.app.state.job_repository.jobs_by_id) == 1


def test_reject_task_resumes_instance_to_rejected_end(client: TestClient) -> None:
    token, org_id, user_id = register_login_create_org(client, "owner@example.com")
    instance = create_activate_start(client, token, org_id, approval_workflow_payload(user_id))
    task = client.get(f"/api/orgs/{org_id}/tasks", headers={"Authorization": f"Bearer {token}"}).json()[0]

    response = client.post(
        f"/api/orgs/{org_id}/tasks/{task['id']}/reject",
        json={"revision": task["revision"]},
        headers={"Authorization": f"Bearer {token}"},
    )
    instance_response = client.get(
        f"/api/orgs/{org_id}/instances/{instance['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["decision"] == "reject"
    assert instance_response.json()["context"]["result"] == "rejected"


def test_duplicate_task_decision_returns_conflict(client: TestClient) -> None:
    token, org_id, user_id = register_login_create_org(client, "owner@example.com")
    create_activate_start(client, token, org_id, approval_workflow_payload(user_id))
    task = client.get(f"/api/orgs/{org_id}/tasks", headers={"Authorization": f"Bearer {token}"}).json()[0]
    client.post(
        f"/api/orgs/{org_id}/tasks/{task['id']}/approve",
        json={"revision": task["revision"]},
        headers={"Authorization": f"Bearer {token}"},
    )

    response = client.post(
        f"/api/orgs/{org_id}/tasks/{task['id']}/approve",
        json={"revision": task["revision"]},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 409


def test_task_assigned_to_another_user_is_forbidden(client: TestClient) -> None:
    owner_token, org_id, owner_id = register_login_create_org(client, "owner@example.com")
    other_token, _, _ = register_login_create_org(client, "other@example.com")
    create_activate_start(client, owner_token, org_id, approval_workflow_payload(owner_id))
    task = client.get(f"/api/orgs/{org_id}/tasks", headers={"Authorization": f"Bearer {owner_token}"}).json()[0]

    response = client.post(
        f"/api/orgs/{org_id}/tasks/{task['id']}/approve",
        json={"revision": task["revision"]},
        headers={"Authorization": f"Bearer {other_token}"},
    )

    assert response.status_code == 403
