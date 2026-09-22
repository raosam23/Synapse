from unittest.mock import patch
from uuid import UUID, uuid4

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


def test_delete_project_conflict_when_it_has_team_members(
    api_client: TestClient,
) -> None:
    user = _register_test_user(api_client)
    created = _create_project(api_client, name="Has roster")
    member_response = api_client.post(
        "/api/v1/team-members/",
        json={
            "skills": ["Python"],
            "user_id": user["id"],
            "project_id": created["id"],
        },
    )
    assert member_response.status_code == status.HTTP_201_CREATED

    response = api_client.delete(f"/api/v1/projects/{created['id']}")
    assert response.status_code == status.HTTP_409_CONFLICT
    assert "team members" in response.json()["detail"]


def test_delete_project_conflict_when_it_has_sprints(api_client: TestClient) -> None:
    _register_test_user(api_client)
    created = _create_project(api_client, name="Has sprints")
    plan = api_client.post(
        "/api/v1/sprints/",
        json={"project_id": created["id"], "start_date": "2026-04-06"},
    )
    assert plan.status_code == status.HTTP_201_CREATED

    response = api_client.delete(f"/api/v1/projects/{created['id']}")
    assert response.status_code == status.HTTP_409_CONFLICT
    assert "sprints" in response.json()["detail"]


def test_run_agents_unauthenticated(api_client: TestClient) -> None:
    response = api_client.post(f"/api/v1/projects/{uuid4()}/agents/run")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_run_agents(api_client: TestClient) -> None:
    _register_test_user(api_client)
    created = _create_project(api_client)
    fake = {
        "opinion": "Looks feasible.",
        "tasks": [
            {
                "title": "[Feature]: One",
                "description": "x" * 700,
                "story_points": 3,
            },
            {
                "title": "[Feature]: Two",
                "description": "y" * 700,
                "story_points": 5,
            },
        ],
    }

    with patch(
        "app.api.routes.projects.run_analyze_requirements",
        return_value=fake,
    ):
        response = api_client.post(f"/api/v1/projects/{created['id']}/agents/run")

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["project_id"] == created["id"]
    assert "2 backlog" in body["message"]

    project = api_client.get(f"/api/v1/projects/{created['id']}").json()
    assert project["ai_opinion"] == "Looks feasible."

    tasks = api_client.get(
        "/api/v1/tasks/",
        params={"project_id": created["id"]},
    ).json()
    assert len(tasks) == 2
    assert all(task["status"] == "backlog" for task in tasks)
    assert all(task["sprint_id"] is None for task in tasks)

    second = api_client.post(f"/api/v1/projects/{created['id']}/agents/run")
    assert second.status_code == status.HTTP_409_CONFLICT


def test_run_agents_not_found(api_client: TestClient) -> None:
    _register_test_user(api_client)
    response = api_client.post(f"/api/v1/projects/{uuid4()}/agents/run")
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_run_agents_hides_other_users_project(api_client: TestClient) -> None:
    _register_test_user(api_client)
    created = _create_project(api_client)
    _register_test_user(api_client)

    response = api_client.post(f"/api/v1/projects/{created['id']}/agents/run")
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_plan_sprint_unauthenticated(api_client: TestClient) -> None:
    response = api_client.post(f"/api/v1/projects/{uuid4()}/agents/plan-sprint")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_plan_sprint_requires_analysis(api_client: TestClient) -> None:
    user = _register_test_user(api_client)
    created = _create_project(api_client)
    member = api_client.post(
        "/api/v1/team-members/",
        json={
            "skills": ["Python"],
            "user_id": user["id"],
            "project_id": created["id"],
        },
    )
    assert member.status_code == status.HTTP_201_CREATED
    sprints = api_client.post(
        "/api/v1/sprints/",
        json={"project_id": created["id"], "start_date": "2026-04-06"},
    )
    assert sprints.status_code == status.HTTP_201_CREATED
    task = api_client.post(
        "/api/v1/tasks/",
        json={
            "title": "Backlog item",
            "project_id": created["id"],
            "story_points": 3,
        },
    )
    assert task.status_code == status.HTTP_201_CREATED

    response = api_client.post(f"/api/v1/projects/{created['id']}/agents/plan-sprint")
    assert response.status_code == status.HTTP_409_CONFLICT
    assert "not been analyzed" in response.json()["detail"]


def test_plan_sprint(api_client: TestClient) -> None:
    user = _register_test_user(api_client)
    created = _create_project(api_client)

    opinion = api_client.put(
        f"/api/v1/projects/{created['id']}",
        json={"ai_opinion": "Looks feasible."},
    )
    assert opinion.status_code == status.HTTP_200_OK

    member_response = api_client.post(
        "/api/v1/team-members/",
        json={
            "skills": ["Python"],
            "user_id": user["id"],
            "project_id": created["id"],
        },
    )
    assert member_response.status_code == status.HTTP_201_CREATED
    member = member_response.json()

    sprints_response = api_client.post(
        "/api/v1/sprints/",
        json={"project_id": created["id"], "start_date": "2026-04-06"},
    )
    assert sprints_response.status_code == status.HTTP_201_CREATED
    first_sprint = sprints_response.json()[0]

    pull_me = api_client.post(
        "/api/v1/tasks/",
        json={
            "title": "[Feature]: Pull me",
            "project_id": created["id"],
            "story_points": 3,
        },
    )
    assert pull_me.status_code == status.HTTP_201_CREATED
    leave_me = api_client.post(
        "/api/v1/tasks/",
        json={
            "title": "[Feature]: Leave me",
            "project_id": created["id"],
            "story_points": 5,
        },
    )
    assert leave_me.status_code == status.HTTP_201_CREATED
    pull_me_body = pull_me.json()
    leave_me_body = leave_me.json()

    fake = {
        "assignments": [
            {
                "task_id": UUID(pull_me_body["id"]),
                "member_id": UUID(member["id"]),
            }
        ]
    }

    with patch(
        "app.api.routes.projects.run_plan_sprint",
        return_value=fake,
    ):
        response = api_client.post(
            f"/api/v1/projects/{created['id']}/agents/plan-sprint"
        )

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["project_id"] == created["id"]
    assert "Assigned 1" in body["message"]

    tasks = api_client.get(
        "/api/v1/tasks/",
        params={"project_id": created["id"]},
    ).json()
    by_id = {task["id"]: task for task in tasks}

    assigned = by_id[pull_me_body["id"]]
    assert assigned["status"] == "todo"
    assert assigned["sprint_id"] == first_sprint["id"]
    assert assigned["assignee_id"] == member["id"]

    leftover = by_id[leave_me_body["id"]]
    assert leftover["status"] == "backlog"
    assert leftover["sprint_id"] is None
    assert leftover["assignee_id"] is None


def test_plan_sprint_ignores_duplicate_task_assignments(
    api_client: TestClient,
) -> None:
    user = _register_test_user(api_client)
    created = _create_project(api_client)
    assert (
        api_client.put(
            f"/api/v1/projects/{created['id']}",
            json={"ai_opinion": "Looks feasible."},
        ).status_code
        == status.HTTP_200_OK
    )
    member = api_client.post(
        "/api/v1/team-members/",
        json={
            "skills": ["Python"],
            "user_id": user["id"],
            "project_id": created["id"],
        },
    ).json()
    assert (
        api_client.post(
            "/api/v1/sprints/",
            json={"project_id": created["id"], "start_date": "2026-04-06"},
        ).status_code
        == status.HTTP_201_CREATED
    )
    task = api_client.post(
        "/api/v1/tasks/",
        json={
            "title": "[Feature]: Once only",
            "project_id": created["id"],
            "story_points": 3,
        },
    ).json()
    other = api_client.post(
        "/api/v1/tasks/",
        json={
            "title": "[Feature]: Spare capacity",
            "project_id": created["id"],
            "story_points": 3,
        },
    ).json()

    fake = {
        "assignments": [
            {"task_id": UUID(task["id"]), "member_id": UUID(member["id"])},
            {"task_id": UUID(task["id"]), "member_id": UUID(member["id"])},
            {"task_id": UUID(other["id"]), "member_id": UUID(member["id"])},
        ]
    }
    with patch(
        "app.api.routes.projects.run_plan_sprint",
        return_value=fake,
    ):
        response = api_client.post(
            f"/api/v1/projects/{created['id']}/agents/plan-sprint"
        )

    assert response.status_code == status.HTTP_200_OK
    # Duplicate row must not inflate the count (2 unique tasks, not 3).
    assert "Assigned 2" in response.json()["message"]

    tasks = api_client.get(
        "/api/v1/tasks/",
        params={"project_id": created["id"]},
    ).json()
    by_id = {t["id"]: t for t in tasks}
    assert by_id[task["id"]]["status"] == "todo"
    assert by_id[other["id"]]["status"] == "todo"
    assert by_id[task["id"]]["assignee_id"] == member["id"]


def test_plan_sprint_second_run_respects_remaining_capacity(
    api_client: TestClient,
) -> None:
    """In-sprint points count against the 8-point cap on a later plan-sprint."""
    user = _register_test_user(api_client)
    created = _create_project(api_client)
    assert (
        api_client.put(
            f"/api/v1/projects/{created['id']}",
            json={"ai_opinion": "Looks feasible."},
        ).status_code
        == status.HTTP_200_OK
    )
    member = api_client.post(
        "/api/v1/team-members/",
        json={
            "skills": ["Python"],
            "user_id": user["id"],
            "project_id": created["id"],
        },
    ).json()
    assert (
        api_client.post(
            "/api/v1/sprints/",
            json={"project_id": created["id"], "start_date": "2026-04-06"},
        ).status_code
        == status.HTTP_201_CREATED
    )

    first = api_client.post(
        "/api/v1/tasks/",
        json={
            "title": "[Feature]: First eight",
            "project_id": created["id"],
            "story_points": 8,
        },
    ).json()
    second = api_client.post(
        "/api/v1/tasks/",
        json={
            "title": "[Feature]: Should stay backlog",
            "project_id": created["id"],
            "story_points": 3,
        },
    ).json()

    with patch(
        "app.api.routes.projects.run_plan_sprint",
        return_value={
            "assignments": [
                {"task_id": UUID(first["id"]), "member_id": UUID(member["id"])}
            ]
        },
    ):
        first_run = api_client.post(
            f"/api/v1/projects/{created['id']}/agents/plan-sprint"
        )
    assert first_run.status_code == status.HTTP_200_OK
    assert "Assigned 1" in first_run.json()["message"]

    with patch(
        "app.api.routes.projects.run_plan_sprint",
        return_value={
            "assignments": [
                {"task_id": UUID(second["id"]), "member_id": UUID(member["id"])}
            ]
        },
    ) as mocked:
        second_run = api_client.post(
            f"/api/v1/projects/{created['id']}/agents/plan-sprint"
        )

    assert second_run.status_code == status.HTTP_200_OK
    assert "Assigned 0" in second_run.json()["message"]
    # No leftover capacity => planner gets an empty candidate list.
    mocked.assert_called_once()
    assert mocked.call_args.args[0] == []

    tasks = api_client.get(
        "/api/v1/tasks/",
        params={"project_id": created["id"]},
    ).json()
    by_id = {task["id"]: task for task in tasks}
    assert by_id[first["id"]]["status"] == "todo"
    assert by_id[second["id"]]["status"] == "backlog"
    assert by_id[second["id"]]["sprint_id"] is None


def test_plan_sprint_not_found(api_client: TestClient) -> None:
    _register_test_user(api_client)
    response = api_client.post(f"/api/v1/projects/{uuid4()}/agents/plan-sprint")
    assert response.status_code == status.HTTP_404_NOT_FOUND
