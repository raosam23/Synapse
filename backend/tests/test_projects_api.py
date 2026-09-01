from uuid import uuid4

from fastapi import status
from fastapi.testclient import TestClient


def _register_test_user(
    api_client: TestClient,
    *,
    email: str | None = None,
    password: str | None = None,
    name: str | None = None,
) -> dict:
    response = api_client.post(
        "/api/v1/auth/register",
        json={
            "email": email or f"some_user{uuid4()}@example.com",
            "password": password or "some_users_password",
            "name": name or "Some User",
        },
    )
    assert response.status_code == status.HTTP_201_CREATED
    return response.json()


def _create_project(
    api_client: TestClient,
    *,
    name: str = "Synapse v1",
    requirements: str = "Paste requirements and get a backlog.",
    duration_weeks: int = 8,
) -> dict:
    response = api_client.post(
        "/api/v1/projects/",
        json={
            "name": name,
            "requirements": requirements,
            "duration_weeks": duration_weeks,
        },
    )
    assert response.status_code == status.HTTP_201_CREATED
    return response.json()


def test_create_project(api_client: TestClient) -> None:
    user = _register_test_user(api_client)
    response = api_client.post(
        "/api/v1/projects/",
        json={
            "name": "Synapse v1",
            "requirements": "Paste requirements and get a backlog.",
            "duration_weeks": 8,
        },
    )
    assert response.status_code == status.HTTP_201_CREATED
    body = response.json()
    assert body["name"] == "Synapse v1"
    assert body["requirements"] == "Paste requirements and get a backlog."
    assert body["duration_weeks"] == 8
    assert body["sprint_length_weeks"] == 2
    assert body["status"] == "planning"
    assert body["ai_opinion"] is None
    assert body["created_by_id"] == user["id"]


def test_create_project_unauthenticated(api_client: TestClient) -> None:
    response = api_client.post(
        "/api/v1/projects/",
        json={
            "name": "Synapse v1",
            "requirements": "Paste requirements and get a backlog.",
            "duration_weeks": 8,
        },
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_create_project_validation_error(api_client: TestClient) -> None:
    _register_test_user(api_client)
    response = api_client.post(
        "/api/v1/projects/",
        json={
            "name": "Synapse v1",
            "requirements": "Paste requirements and get a backlog.",
            "duration_weeks": 0,
        },
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_get_projects(api_client: TestClient) -> None:
    _register_test_user(api_client)
    created = _create_project(api_client, name="Grace Hopper")

    response = api_client.get("/api/v1/projects/")
    assert response.status_code == status.HTTP_200_OK
    projects = response.json()
    match = next(p for p in projects if p["id"] == created["id"])
    assert match["name"] == "Grace Hopper"
    assert match["sprint_length_weeks"] == 2


def test_get_project(api_client: TestClient) -> None:
    _register_test_user(api_client)
    created = _create_project(api_client, name="Alan Turing")

    response = api_client.get(f"/api/v1/projects/{created['id']}")
    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["id"] == created["id"]
    assert body["name"] == "Alan Turing"


def test_get_project_not_found(api_client: TestClient) -> None:
    _register_test_user(api_client)

    response = api_client.get(f"/api/v1/projects/{uuid4()}")
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_get_project_hides_other_users_project(api_client: TestClient) -> None:
    _register_test_user(api_client)
    created = _create_project(api_client)
    _register_test_user(api_client)

    response = api_client.get(f"/api/v1/projects/{created['id']}")
    assert response.status_code == status.HTTP_404_NOT_FOUND

    list_response = api_client.get("/api/v1/projects/")
    assert list_response.status_code == status.HTTP_200_OK
    assert all(p["id"] != created["id"] for p in list_response.json())


def test_update_project(api_client: TestClient) -> None:
    _register_test_user(api_client)
    created = _create_project(api_client, name="Lisa Simpson")

    response = api_client.put(
        f"/api/v1/projects/{created['id']}",
        json={
            "name": "Lisa Manobal",
            "status": "active",
            "ai_opinion": "Looks feasible.",
        },
    )
    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["id"] == created["id"]
    assert body["name"] == "Lisa Manobal"
    assert body["status"] == "active"
    assert body["ai_opinion"] == "Looks feasible."
    assert body["duration_weeks"] == created["duration_weeks"]


def test_update_project_not_found(api_client: TestClient) -> None:
    _register_test_user(api_client)

    response = api_client.put(
        f"/api/v1/projects/{uuid4()}",
        json={"name": "Lisa Manobal"},
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_update_project_validation_error(api_client: TestClient) -> None:
    _register_test_user(api_client)
    response = api_client.put(f"/api/v1/projects/{uuid4()}", json={"name": None})
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_update_project_rejects_null_duration_weeks(api_client: TestClient) -> None:
    _register_test_user(api_client)
    response = api_client.put(
        f"/api/v1/projects/{uuid4()}",
        json={"duration_weeks": None},
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_delete_project(api_client: TestClient) -> None:
    _register_test_user(api_client)
    created = _create_project(api_client, name="Jennie Kim")

    project_id = created["id"]
    response = api_client.delete(f"/api/v1/projects/{project_id}")
    assert response.status_code == status.HTTP_204_NO_CONTENT

    response = api_client.get(f"/api/v1/projects/{project_id}")
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_delete_project_not_found(api_client: TestClient) -> None:
    _register_test_user(api_client)
    response = api_client.delete(f"/api/v1/projects/{uuid4()}")
    assert response.status_code == status.HTTP_404_NOT_FOUND
