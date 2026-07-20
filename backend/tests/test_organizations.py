import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import (
    organization_member_repository_dependency,
    organization_repository_dependency,
    user_repository_dependency,
)
from app.domain.auth.repository import UserRepository
from app.domain.orgs.repository import OrganizationMemberRepository, OrganizationRepository
from app.main import create_app
from tests.fakes import (
    InMemoryOrganizationMemberRepository,
    InMemoryOrganizationRepository,
    InMemoryUserRepository,
)


@pytest.fixture
def user_repository() -> InMemoryUserRepository:
    return InMemoryUserRepository()


@pytest.fixture
def organization_repository() -> InMemoryOrganizationRepository:
    return InMemoryOrganizationRepository()


@pytest.fixture
def member_repository() -> InMemoryOrganizationMemberRepository:
    return InMemoryOrganizationMemberRepository()


@pytest.fixture
def client(
    user_repository: InMemoryUserRepository,
    organization_repository: InMemoryOrganizationRepository,
    member_repository: InMemoryOrganizationMemberRepository,
) -> TestClient:
    app = create_app()

    async def override_user_repository() -> UserRepository:
        return user_repository

    async def override_organization_repository() -> OrganizationRepository:
        return organization_repository

    async def override_member_repository() -> OrganizationMemberRepository:
        return member_repository

    app.dependency_overrides[user_repository_dependency] = override_user_repository
    app.dependency_overrides[organization_repository_dependency] = override_organization_repository
    app.dependency_overrides[organization_member_repository_dependency] = override_member_repository
    return TestClient(app)


def register_and_login(client: TestClient, email: str) -> str:
    client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": "correct-horse-battery",
            "full_name": "Workflow User",
        },
    )
    response = client.post(
        "/api/auth/login",
        json={"email": email, "password": "correct-horse-battery"},
    )
    return response.json()["access_token"]


def test_create_organization_makes_current_user_owner(client: TestClient) -> None:
    token = register_and_login(client, "owner@example.com")

    response = client.post(
        "/api/orgs",
        json={"name": "Acme Approvals"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 201
    assert response.json()["name"] == "Acme Approvals"
    assert response.json()["role"] == "owner"


def test_list_organizations_returns_only_current_users_orgs(client: TestClient) -> None:
    owner_token = register_and_login(client, "owner@example.com")
    other_token = register_and_login(client, "other@example.com")

    client.post(
        "/api/orgs",
        json={"name": "Owner Org"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    client.post(
        "/api/orgs",
        json={"name": "Other Org"},
        headers={"Authorization": f"Bearer {other_token}"},
    )

    response = client.get("/api/orgs", headers={"Authorization": f"Bearer {owner_token}"})

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": response.json()[0]["id"],
            "name": "Owner Org",
            "role": "owner",
        }
    ]


def test_get_organization_requires_membership(client: TestClient) -> None:
    owner_token = register_and_login(client, "owner@example.com")
    other_token = register_and_login(client, "other@example.com")
    create_response = client.post(
        "/api/orgs",
        json={"name": "Private Org"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )

    response = client.get(
        f"/api/orgs/{create_response.json()['id']}",
        headers={"Authorization": f"Bearer {other_token}"},
    )

    assert response.status_code == 403


def test_get_organization_for_member(client: TestClient) -> None:
    token = register_and_login(client, "owner@example.com")
    create_response = client.post(
        "/api/orgs",
        json={"name": "Member Org"},
        headers={"Authorization": f"Bearer {token}"},
    )

    response = client.get(
        f"/api/orgs/{create_response.json()['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Member Org"
    assert response.json()["role"] == "owner"


def test_list_organization_members_returns_user_friendly_members(client: TestClient) -> None:
    token = register_and_login(client, "owner@example.com")
    create_response = client.post(
        "/api/orgs",
        json={"name": "Member Directory Org"},
        headers={"Authorization": f"Bearer {token}"},
    )

    response = client.get(
        f"/api/orgs/{create_response.json()['id']}/members",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": response.json()[0]["id"],
            "user_id": response.json()[0]["user_id"],
            "email": "owner@example.com",
            "full_name": "Workflow User",
            "role": "owner",
        }
    ]


def test_owner_can_add_registered_user_to_organization(client: TestClient) -> None:
    owner_token = register_and_login(client, "owner@example.com")
    register_and_login(client, "member@example.com")
    create_response = client.post(
        "/api/orgs",
        json={"name": "Team Org"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )

    response = client.post(
        f"/api/orgs/{create_response.json()['id']}/members",
        json={"email": "member@example.com", "role": "member"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )

    assert response.status_code == 201
    assert response.json()["email"] == "member@example.com"
    assert response.json()["role"] == "member"


def test_add_organization_member_requires_registered_user(client: TestClient) -> None:
    owner_token = register_and_login(client, "owner@example.com")
    create_response = client.post(
        "/api/orgs",
        json={"name": "Team Org"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )

    response = client.post(
        f"/api/orgs/{create_response.json()['id']}/members",
        json={"email": "missing@example.com", "role": "member"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )

    assert response.status_code == 404


def test_add_organization_member_rejects_duplicates(client: TestClient) -> None:
    owner_token = register_and_login(client, "owner@example.com")
    register_and_login(client, "member@example.com")
    create_response = client.post(
        "/api/orgs",
        json={"name": "Team Org"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    client.post(
        f"/api/orgs/{create_response.json()['id']}/members",
        json={"email": "member@example.com", "role": "member"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )

    response = client.post(
        f"/api/orgs/{create_response.json()['id']}/members",
        json={"email": "member@example.com", "role": "member"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )

    assert response.status_code == 409


def test_add_organization_member_rejects_owner_role(client: TestClient) -> None:
    owner_token = register_and_login(client, "owner@example.com")
    register_and_login(client, "member@example.com")
    create_response = client.post(
        "/api/orgs",
        json={"name": "Team Org"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )

    response = client.post(
        f"/api/orgs/{create_response.json()['id']}/members",
        json={"email": "member@example.com", "role": "owner"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )

    assert response.status_code == 403
