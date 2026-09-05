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


def _create_team_member(
    api_client: TestClient,
    *,
    skills: list[str],
    user_id: str,
    project_id: str,
) -> dict:
    response = api_client.post(
        "/api/v1/team-members/",
        json={
            "skills": skills,
            "user_id": user_id,
            "project_id": project_id,
        },
    )
    assert response.status_code == status.HTTP_201_CREATED
    return response.json()


def test_create_task_without_assignee(api_client: TestClient) -> None:
    user = _register_test_user(api_client)
    project = _create_project(api_client)
    response = api_client.post(
        "/api/v1/tasks/",
        json={
            "title": "Write unit tests",
            "description": "Cover project_id on tasks",
            "project_id": project["id"],
        },
    )
    assert response.status_code == status.HTTP_201_CREATED
    body = response.json()
    assert body["title"] == "Write unit tests"
    assert body["assignee_id"] is None
    assert body["project_id"] == project["id"]
    assert body["created_by_id"] == user["id"]
    assert body["status"] == "backlog"


def test_create_task_missing_project_returns_404(api_client: TestClient) -> None:
    _register_test_user(api_client)
    response = api_client.post(
        "/api/v1/tasks/",
        json={
            "title": "Orphan task",
            "project_id": str(uuid4()),
        },
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_create_task_assignee_on_other_project_returns_409(
    api_client: TestClient,
) -> None:
    user = _register_test_user(api_client)
    project_a = _create_project(api_client, name="Project A")
    project_b = _create_project(api_client, name="Project B")
    member_on_b = _create_team_member(
        api_client,
        skills=["Python"],
        user_id=user["id"],
        project_id=project_b["id"],
    )

    response = api_client.post(
        "/api/v1/tasks/",
        json={
            "title": "Assign across projects",
            "assignee_id": member_on_b["id"],
            "project_id": project_a["id"],
        },
    )
    assert response.status_code == status.HTTP_409_CONFLICT


def test_get_tasks_filter_by_project(api_client: TestClient) -> None:
    _register_test_user(api_client)
    project_a = _create_project(api_client, name="Project A")
    project_b = _create_project(api_client, name="Project B")

    task_a = api_client.post(
        "/api/v1/tasks/",
        json={"title": "Task A", "project_id": project_a["id"]},
    )
    assert task_a.status_code == status.HTTP_201_CREATED
    task_b = api_client.post(
        "/api/v1/tasks/",
        json={"title": "Task B", "project_id": project_b["id"]},
    )
    assert task_b.status_code == status.HTTP_201_CREATED

    response = api_client.get("/api/v1/tasks/", params={"project_id": project_a["id"]})
    assert response.status_code == status.HTTP_200_OK
    tasks = response.json()
    ids = {t["id"] for t in tasks}
    assert task_a.json()["id"] in ids
    assert task_b.json()["id"] not in ids
    assert all(t["project_id"] == project_a["id"] for t in tasks)


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


def test_create_task_unknown_sprint_returns_404(api_client: TestClient) -> None:
    _register_test_user(api_client)
    project = _create_project(api_client)
    response = api_client.post(
        "/api/v1/tasks/",
        json={
            "title": "Unknown sprint",
            "project_id": project["id"],
            "sprint_id": str(uuid4()),
        },
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_create_task_sprint_on_other_project_returns_409(
    api_client: TestClient,
) -> None:
    _register_test_user(api_client)
    project_a = _create_project(api_client, name="Project A")
    project_b = _create_project(api_client, name="Project B")
    sprint_on_b = _plan_sprints(api_client, project_id=project_b["id"])[0]

    response = api_client.post(
        "/api/v1/tasks/",
        json={
            "title": "Wrong sprint project",
            "project_id": project_a["id"],
            "sprint_id": sprint_on_b["id"],
        },
    )
    assert response.status_code == status.HTTP_409_CONFLICT


def test_create_task_with_sprint_on_same_project(api_client: TestClient) -> None:
    _register_test_user(api_client)
    project = _create_project(api_client)
    sprint = _plan_sprints(api_client, project_id=project["id"])[0]
    response = api_client.post(
        "/api/v1/tasks/",
        json={
            "title": "In sprint 1",
            "project_id": project["id"],
            "sprint_id": sprint["id"],
        },
    )
    assert response.status_code == status.HTTP_201_CREATED
    body = response.json()
    assert body["sprint_id"] == sprint["id"]
    assert body["project_id"] == project["id"]


def test_update_task_sprint_on_other_project_returns_409(
    api_client: TestClient,
) -> None:
    _register_test_user(api_client)
    project_a = _create_project(api_client, name="Project A")
    project_b = _create_project(api_client, name="Project B")
    sprint_on_b = _plan_sprints(api_client, project_id=project_b["id"])[0]
    created = api_client.post(
        "/api/v1/tasks/",
        json={"title": "Backlog", "project_id": project_a["id"]},
    )
    assert created.status_code == status.HTTP_201_CREATED

    response = api_client.put(
        f"/api/v1/tasks/{created.json()['id']}",
        json={"sprint_id": sprint_on_b["id"]},
    )
    assert response.status_code == status.HTTP_409_CONFLICT


def test_delete_task_with_comments_succeeds(api_client: TestClient) -> None:
    _register_test_user(api_client)
    project = _create_project(api_client)
    created = api_client.post(
        "/api/v1/tasks/",
        json={"title": "Commented task", "project_id": project["id"]},
    )
    assert created.status_code == status.HTTP_201_CREATED
    task_id = created.json()["id"]

    comment = api_client.post(
        "/api/v1/comments/",
        json={"task_id": task_id, "body": "Progress note"},
    )
    assert comment.status_code == status.HTTP_201_CREATED
    comment_id = comment.json()["id"]

    response = api_client.delete(f"/api/v1/tasks/{task_id}")
    assert response.status_code == status.HTTP_204_NO_CONTENT

    missing_task = api_client.get(f"/api/v1/tasks/{task_id}")
    assert missing_task.status_code == status.HTTP_404_NOT_FOUND
    missing_comment = api_client.get(f"/api/v1/comments/{comment_id}")
    assert missing_comment.status_code == status.HTTP_404_NOT_FOUND
