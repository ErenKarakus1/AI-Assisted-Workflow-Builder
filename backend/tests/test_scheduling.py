from datetime import UTC, datetime, timedelta

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
from app.domain.scheduling.service import SchedulerService
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


def build_client():
    app = create_app()
    repos = {
        "users": InMemoryUserRepository(),
        "orgs": InMemoryOrganizationRepository(),
        "members": InMemoryOrganizationMemberRepository(),
        "workflows": InMemoryWorkflowRepository(),
        "instances": InMemoryWorkflowInstanceRepository(),
        "events": InMemoryInstanceEventRepository(),
        "tasks": InMemoryTaskRepository(),
        "jobs": InMemoryScheduledJobRepository(),
    }
    app.dependency_overrides[user_repository_dependency] = lambda: repos["users"]
    app.dependency_overrides[organization_repository_dependency] = lambda: repos["orgs"]
    app.dependency_overrides[organization_member_repository_dependency] = lambda: repos["members"]
    app.dependency_overrides[workflow_repository_dependency] = lambda: repos["workflows"]
    app.dependency_overrides[workflow_instance_repository_dependency] = lambda: repos["instances"]
    app.dependency_overrides[instance_event_repository_dependency] = lambda: repos["events"]
    app.dependency_overrides[task_repository_dependency] = lambda: repos["tasks"]
    app.dependency_overrides[scheduled_job_repository_dependency] = lambda: repos["jobs"]
    return TestClient(app), repos


def register_login_create_org(client: TestClient) -> tuple[str, str]:
    client.post(
        "/api/auth/register",
        json={
            "email": "owner@example.com",
            "password": "correct-horse-battery",
            "full_name": "Workflow User",
        },
    )
    token = client.post(
        "/api/auth/login",
        json={"email": "owner@example.com", "password": "correct-horse-battery"},
    ).json()["access_token"]
    org_id = client.post(
        "/api/orgs",
        json={"name": "Owner Org"},
        headers={"Authorization": f"Bearer {token}"},
    ).json()["id"]
    return token, org_id


def delay_workflow_payload(seconds: int = 0) -> dict:
    return {
        "name": "Delay Flow",
        "nodes": [
            {"id": "start-1", "type": "start", "position": {}, "data": {}},
            {"id": "delay-1", "type": "delay", "position": {}, "data": {"seconds": seconds}},
            {"id": "end-1", "type": "end", "position": {}, "data": {"result": "done"}},
        ],
        "edges": [
            {"id": "edge-1", "source": "start-1", "target": "delay-1", "label": None, "data": {}},
            {"id": "edge-2", "source": "delay-1", "target": "end-1", "label": None, "data": {}},
        ],
    }


def create_activate_start_delay(client: TestClient, token: str, org_id: str, seconds: int = 0) -> dict:
    workflow_id = client.post(
        f"/api/orgs/{org_id}/workflows",
        json=delay_workflow_payload(seconds),
        headers={"Authorization": f"Bearer {token}"},
    ).json()["id"]
    client.post(
        f"/api/orgs/{org_id}/workflows/{workflow_id}/activate",
        headers={"Authorization": f"Bearer {token}"},
    )
    return client.post(
        f"/api/orgs/{org_id}/workflows/{workflow_id}/instances",
        json={"input": {}},
        headers={"Authorization": f"Bearer {token}"},
    ).json()


def test_delay_node_creates_job_and_waits() -> None:
    client, repos = build_client()
    token, org_id = register_login_create_org(client)

    instance = create_activate_start_delay(client, token, org_id, seconds=60)

    assert instance["status"] == "waiting"
    assert len(repos["jobs"].jobs_by_id) == 1
    events = client.get(
        f"/api/orgs/{org_id}/instances/{instance['id']}/events",
        headers={"Authorization": f"Bearer {token}"},
    ).json()
    assert events[-1]["type"] == "delay_scheduled"


def test_due_delay_job_resumes_instance() -> None:
    client, repos = build_client()
    token, org_id = register_login_create_org(client)
    instance = create_activate_start_delay(client, token, org_id)

    processed = run_scheduler(repos)
    instance_response = client.get(
        f"/api/orgs/{org_id}/instances/{instance['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert processed == 1
    assert instance_response.json()["status"] == "completed"
    assert instance_response.json()["context"]["result"] == "done"


def test_completed_delay_job_is_not_processed_twice() -> None:
    client, repos = build_client()
    token, org_id = register_login_create_org(client)
    create_activate_start_delay(client, token, org_id)

    assert run_scheduler(repos) == 1
    assert run_scheduler(repos) == 0


def run_scheduler(repos) -> int:
    import asyncio

    return asyncio.run(
        SchedulerService(
            jobs=repos["jobs"],
            workflows=repos["workflows"],
            instances=repos["instances"],
            events=repos["events"],
        ).process_due_jobs(now=datetime.now(UTC) + timedelta(seconds=1))
    )
