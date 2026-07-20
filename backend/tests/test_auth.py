import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import user_repository_dependency
from app.domain.auth.repository import UserRepository
from app.main import create_app
from tests.fakes import InMemoryUserRepository


@pytest.fixture
def user_repository() -> InMemoryUserRepository:
    return InMemoryUserRepository()


@pytest.fixture
def client(user_repository: InMemoryUserRepository) -> TestClient:
    app = create_app()

    async def override_user_repository() -> UserRepository:
        return user_repository

    app.dependency_overrides[user_repository_dependency] = override_user_repository
    return TestClient(app)


def test_register_user(client: TestClient) -> None:
    response = client.post(
        "/api/auth/register",
        json={
            "email": "EREN@example.com",
            "password": "correct-horse-battery",
            "full_name": "Eren Karakus",
        },
    )

    assert response.status_code == 201
    assert response.json()["email"] == "eren@example.com"
    assert response.json()["full_name"] == "Eren Karakus"
    assert "hashed_password" not in response.json()


def test_register_duplicate_email_returns_conflict(client: TestClient) -> None:
    payload = {
        "email": "eren@example.com",
        "password": "correct-horse-battery",
        "full_name": "Eren Karakus",
    }

    assert client.post("/api/auth/register", json=payload).status_code == 201
    response = client.post("/api/auth/register", json=payload)

    assert response.status_code == 409


def test_login_and_me(client: TestClient) -> None:
    register_response = client.post(
        "/api/auth/register",
        json={
            "email": "eren@example.com",
            "password": "correct-horse-battery",
            "full_name": "Eren Karakus",
        },
    )

    login_response = client.post(
        "/api/auth/login",
        json={"email": "eren@example.com", "password": "correct-horse-battery"},
    )

    assert register_response.status_code == 201
    assert login_response.status_code == 200
    tokens = login_response.json()
    assert tokens["token_type"] == "bearer"
    assert tokens["access_token"]
    assert tokens["refresh_token"]

    me_response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )

    assert me_response.status_code == 200
    assert me_response.json()["email"] == "eren@example.com"


def test_login_with_wrong_password_returns_unauthorized(client: TestClient) -> None:
    client.post(
        "/api/auth/register",
        json={
            "email": "eren@example.com",
            "password": "correct-horse-battery",
            "full_name": "Eren Karakus",
        },
    )

    response = client.post(
        "/api/auth/login",
        json={"email": "eren@example.com", "password": "wrong-password"},
    )

    assert response.status_code == 401


def test_refresh_token_returns_new_token_pair(client: TestClient) -> None:
    client.post(
        "/api/auth/register",
        json={
            "email": "eren@example.com",
            "password": "correct-horse-battery",
            "full_name": "Eren Karakus",
        },
    )
    login_response = client.post(
        "/api/auth/login",
        json={"email": "eren@example.com", "password": "correct-horse-battery"},
    )

    response = client.post(
        "/api/auth/refresh",
        json={"refresh_token": login_response.json()["refresh_token"]},
    )

    assert response.status_code == 200
    assert response.json()["access_token"]
    assert response.json()["refresh_token"]
