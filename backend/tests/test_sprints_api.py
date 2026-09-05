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


def _plan_sprints(
    api_client: TestClient,
    *,
    project_id: str,
    start_date: str = "2026-04-06",
) -> list[dict]:
    response = api_client.post(
        "/api/v1/sprints/",
        json={"project_id": project_id, "start_date": start_date},
    )
    assert response.status_code == status.HTTP_201_CREATED
    return response.json()


def test_create_sprints_unauthenticated(api_client: TestClient) -> None:
    response = api_client.post(
        "/api/v1/sprints/",
        json={"project_id": str(uuid4()), "start_date": "2026-04-06"},
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_create_sprints_for_eight_week_project(api_client: TestClient) -> None:
    _register_test_user(api_client)
    project = _create_project(api_client, duration_weeks=8)
    sprints = _plan_sprints(api_client, project_id=project["id"])

    assert len(sprints) == 4
    assert [sprint["index"] for sprint in sprints] == [1, 2, 3, 4]
    assert all(sprint["project_id"] == project["id"] for sprint in sprints)
    assert sprints[0]["start_date"] == "2026-04-06"
    assert sprints[0]["end_date"] == "2026-04-19"
    assert sprints[1]["start_date"] == "2026-04-20"
    assert sprints[3]["end_date"] == "2026-05-31"


def test_create_sprints_missing_project_returns_404(api_client: TestClient) -> None:
    _register_test_user(api_client)
    response = api_client.post(
        "/api/v1/sprints/",
        json={"project_id": str(uuid4()), "start_date": "2026-04-06"},
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_create_sprints_duration_shorter_than_sprint_returns_400(
    api_client: TestClient,
) -> None:
    _register_test_user(api_client)
    project = _create_project(api_client, duration_weeks=1)
    response = api_client.post(
        "/api/v1/sprints/",
        json={"project_id": project["id"], "start_date": "2026-04-06"},
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_create_sprints_duplicate_returns_409(api_client: TestClient) -> None:
    _register_test_user(api_client)
    project = _create_project(api_client)
    _plan_sprints(api_client, project_id=project["id"])
    response = api_client.post(
        "/api/v1/sprints/",
        json={"project_id": project["id"], "start_date": "2026-04-06"},
    )
    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json()["detail"] == "Sprints already exist for this project"


def test_get_sprints_filter_by_project(api_client: TestClient) -> None:
    _register_test_user(api_client)
    project_a = _create_project(api_client, name="Project A")
    project_b = _create_project(api_client, name="Project B")
    sprints_a = _plan_sprints(api_client, project_id=project_a["id"])
    sprints_b = _plan_sprints(api_client, project_id=project_b["id"])

    response = api_client.get(
        "/api/v1/sprints/", params={"project_id": project_a["id"]}
    )
    assert response.status_code == status.HTTP_200_OK
    listed = response.json()
    ids = {sprint["id"] for sprint in listed}
    assert {sprint["id"] for sprint in sprints_a} <= ids
    assert not {sprint["id"] for sprint in sprints_b} & ids
    assert all(sprint["project_id"] == project_a["id"] for sprint in listed)
    assert [sprint["index"] for sprint in listed] == [1, 2, 3, 4]


def test_get_sprint_by_id(api_client: TestClient) -> None:
    _register_test_user(api_client)
    project = _create_project(api_client)
    created = _plan_sprints(api_client, project_id=project["id"])[0]

    response = api_client.get(f"/api/v1/sprints/{created['id']}")
    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["id"] == created["id"]
    assert body["index"] == 1
    assert body["start_date"] == created["start_date"]


def test_get_sprint_by_id_not_found(api_client: TestClient) -> None:
    _register_test_user(api_client)
    response = api_client.get(f"/api/v1/sprints/{uuid4()}")
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_delete_sprint(api_client: TestClient) -> None:
    _register_test_user(api_client)
    project = _create_project(api_client)
    sprint = _plan_sprints(api_client, project_id=project["id"])[0]

    response = api_client.delete(f"/api/v1/sprints/{sprint['id']}")
    assert response.status_code == status.HTTP_204_NO_CONTENT

    missing = api_client.get(f"/api/v1/sprints/{sprint['id']}")
    assert missing.status_code == status.HTTP_404_NOT_FOUND


def test_delete_sprint_not_found(api_client: TestClient) -> None:
    _register_test_user(api_client)
    response = api_client.delete(f"/api/v1/sprints/{uuid4()}")
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_delete_sprint_with_task_returns_409(api_client: TestClient) -> None:
    _register_test_user(api_client)
    project = _create_project(api_client)
    sprint = _plan_sprints(api_client, project_id=project["id"])[0]
    task = api_client.post(
        "/api/v1/tasks/",
        json={
            "title": "In sprint 1",
            "project_id": project["id"],
            "sprint_id": sprint["id"],
        },
    )
    assert task.status_code == status.HTTP_201_CREATED

    response = api_client.delete(f"/api/v1/sprints/{sprint['id']}")
    assert response.status_code == status.HTTP_409_CONFLICT
