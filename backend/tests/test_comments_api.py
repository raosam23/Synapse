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


def _create_task(
    api_client: TestClient,
    *,
    project_id: str,
    title: str = "Write comments",
) -> dict:
    response = api_client.post(
        "/api/v1/tasks/",
        json={"title": title, "project_id": project_id},
    )
    assert response.status_code == status.HTTP_201_CREATED
    return response.json()


def _create_comment(
    api_client: TestClient,
    *,
    task_id: str,
    body: str = "Looks good.",
) -> dict:
    response = api_client.post(
        "/api/v1/comments/",
        json={"task_id": task_id, "body": body},
    )
    assert response.status_code == status.HTTP_201_CREATED
    return response.json()


def test_create_comment_unauthenticated(api_client: TestClient) -> None:
    response = api_client.post(
        "/api/v1/comments/",
        json={"task_id": str(uuid4()), "body": "Looks good."},
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_create_comment(api_client: TestClient) -> None:
    user = _register_test_user(api_client)
    project = _create_project(api_client)
    task = _create_task(api_client, project_id=project["id"])

    response = api_client.post(
        "/api/v1/comments/",
        json={"task_id": task["id"], "body": "Looks good."},
    )
    assert response.status_code == status.HTTP_201_CREATED
    body = response.json()
    assert body["task_id"] == task["id"]
    assert body["body"] == "Looks good."
    assert body["user_id"] == user["id"]
    assert body["is_ai"] is False
    assert "id" in body
    assert "created_at" in body
    assert "updated_at" in body


def test_create_comment_ignores_client_author_fields(api_client: TestClient) -> None:
    user = _register_test_user(api_client)
    project = _create_project(api_client)
    task = _create_task(api_client, project_id=project["id"])

    response = api_client.post(
        "/api/v1/comments/",
        json={
            "task_id": task["id"],
            "body": "Looks good.",
            "user_id": str(uuid4()),
            "is_ai": True,
        },
    )
    assert response.status_code == status.HTTP_201_CREATED
    body = response.json()
    assert body["user_id"] == user["id"]
    assert body["is_ai"] is False


def test_create_comment_missing_task_returns_404(api_client: TestClient) -> None:
    _register_test_user(api_client)
    response = api_client.post(
        "/api/v1/comments/",
        json={"task_id": str(uuid4()), "body": "Looks good."},
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "Task not found"


def test_create_comment_empty_body_returns_422(api_client: TestClient) -> None:
    _register_test_user(api_client)
    project = _create_project(api_client)
    task = _create_task(api_client, project_id=project["id"])
    response = api_client.post(
        "/api/v1/comments/",
        json={"task_id": task["id"], "body": ""},
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_get_comments_filter_by_task(api_client: TestClient) -> None:
    _register_test_user(api_client)
    project = _create_project(api_client)
    task_a = _create_task(api_client, project_id=project["id"], title="Task A")
    task_b = _create_task(api_client, project_id=project["id"], title="Task B")
    comment_a = _create_comment(api_client, task_id=task_a["id"], body="On A")
    comment_b = _create_comment(api_client, task_id=task_b["id"], body="On B")

    response = api_client.get("/api/v1/comments/", params={"task_id": task_a["id"]})
    assert response.status_code == status.HTTP_200_OK
    listed = response.json()
    ids = {comment["id"] for comment in listed}
    assert comment_a["id"] in ids
    assert comment_b["id"] not in ids
    assert all(comment["task_id"] == task_a["id"] for comment in listed)


def test_get_comments_unknown_task_returns_empty_list(api_client: TestClient) -> None:
    _register_test_user(api_client)
    response = api_client.get("/api/v1/comments/", params={"task_id": str(uuid4())})
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == []


def test_get_comments_newest_first(api_client: TestClient) -> None:
    _register_test_user(api_client)
    project = _create_project(api_client)
    task = _create_task(api_client, project_id=project["id"])
    older = _create_comment(api_client, task_id=task["id"], body="Older")
    newer = _create_comment(api_client, task_id=task["id"], body="Newer")

    response = api_client.get("/api/v1/comments/", params={"task_id": task["id"]})
    assert response.status_code == status.HTTP_200_OK
    listed = response.json()
    ids = [comment["id"] for comment in listed]
    assert ids.index(newer["id"]) < ids.index(older["id"])


def test_get_comment_by_id(api_client: TestClient) -> None:
    _register_test_user(api_client)
    project = _create_project(api_client)
    task = _create_task(api_client, project_id=project["id"])
    created = _create_comment(api_client, task_id=task["id"], body="Looks good.")

    response = api_client.get(f"/api/v1/comments/{created['id']}")
    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["id"] == created["id"]
    assert body["body"] == "Looks good."
    assert body["task_id"] == task["id"]


def test_get_comment_by_id_not_found(api_client: TestClient) -> None:
    _register_test_user(api_client)
    response = api_client.get(f"/api/v1/comments/{uuid4()}")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "Comment not found"


def test_update_comment(api_client: TestClient) -> None:
    _register_test_user(api_client)
    project = _create_project(api_client)
    task = _create_task(api_client, project_id=project["id"])
    created = _create_comment(api_client, task_id=task["id"], body="Old body")

    response = api_client.put(
        f"/api/v1/comments/{created['id']}",
        json={"body": "New body"},
    )
    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["id"] == created["id"]
    assert body["body"] == "New body"


def test_update_comment_omitted_body_leaves_body_unchanged(
    api_client: TestClient,
) -> None:
    _register_test_user(api_client)
    project = _create_project(api_client)
    task = _create_task(api_client, project_id=project["id"])
    created = _create_comment(api_client, task_id=task["id"], body="Keep me")

    response = api_client.put(f"/api/v1/comments/{created['id']}", json={})
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["body"] == "Keep me"


def test_update_comment_null_body_returns_422(api_client: TestClient) -> None:
    _register_test_user(api_client)
    project = _create_project(api_client)
    task = _create_task(api_client, project_id=project["id"])
    created = _create_comment(api_client, task_id=task["id"])

    response = api_client.put(
        f"/api/v1/comments/{created['id']}",
        json={"body": None},
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_update_comment_not_found(api_client: TestClient) -> None:
    _register_test_user(api_client)
    response = api_client.put(
        f"/api/v1/comments/{uuid4()}",
        json={"body": "Nope"},
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_delete_comment(api_client: TestClient) -> None:
    _register_test_user(api_client)
    project = _create_project(api_client)
    task = _create_task(api_client, project_id=project["id"])
    created = _create_comment(api_client, task_id=task["id"])

    response = api_client.delete(f"/api/v1/comments/{created['id']}")
    assert response.status_code == status.HTTP_204_NO_CONTENT

    missing = api_client.get(f"/api/v1/comments/{created['id']}")
    assert missing.status_code == status.HTTP_404_NOT_FOUND


def test_delete_comment_not_found(api_client: TestClient) -> None:
    _register_test_user(api_client)
    response = api_client.delete(f"/api/v1/comments/{uuid4()}")
    assert response.status_code == status.HTTP_404_NOT_FOUND
