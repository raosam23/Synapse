from uuid import uuid4

from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from app.core.config import settings


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


def _insert_assigned_task(*, member_id: str, created_by_id: str) -> None:
    """Insert a task row assigned to member_id, bypassing POST /tasks (#43)."""
    if not settings.DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not configured")
    sync_url = settings.DATABASE_URL.replace(
        "postgresql+asyncpg://", "postgresql+psycopg://"
    )
    engine = create_engine(sync_url)
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO tasks (
                    id, title, status, assignee_id, created_by_id,
                    created_at, updated_at
                )
                VALUES (
                    gen_random_uuid(), :title, 'backlog', :member_id,
                    :created_by_id, NOW(), NOW()
                )
                """
            ),
            {
                "title": "Blocked delete",
                "member_id": member_id,
                "created_by_id": created_by_id,
            },
        )


def test_create_team_member(api_client: TestClient) -> None:
    user = _register_test_user(api_client)
    response = api_client.post(
        "/api/v1/team-members/",
        json={
            "name": "Ada Lovelace",
            "skills": ["Python", "SQL", "Data Analysis", "AI"],
            "user_id": user["id"],
        },
    )
    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["name"] == "Ada Lovelace"
    assert response.json()["user_id"] == user["id"]
    assert response.json()["skills"] == ["Python", "SQL", "Data Analysis", "AI"]


def _create_team_member(
    api_client: TestClient, *, name: str, skills: list[str], user_id: str
) -> dict:
    response = api_client.post(
        "/api/v1/team-members/",
        json={
            "name": name,
            "skills": skills,
            "user_id": user_id,
        },
    )
    assert response.status_code == status.HTTP_201_CREATED
    return response.json()


def test_get_team_members(api_client: TestClient) -> None:
    user = _register_test_user(api_client)
    created = _create_team_member(
        api_client,
        name="Grace Hopper",
        skills=["COBOL", "Compilers"],
        user_id=user["id"],
    )

    response = api_client.get("/api/v1/team-members/")
    assert response.status_code == status.HTTP_200_OK
    members = response.json()
    match = next(m for m in members if m["id"] == created["id"])
    assert match["name"] == "Grace Hopper"
    assert match["skills"] == ["COBOL", "Compilers"]


def test_get_team_member(api_client: TestClient) -> None:
    user = _register_test_user(api_client)
    created = _create_team_member(
        api_client,
        name="Alan Turing",
        skills=["Cryptography"],
        user_id=user["id"],
    )

    response = api_client.get(f"/api/v1/team-members/{created['id']}")
    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["id"] == created["id"]
    assert body["name"] == "Alan Turing"
    assert body["skills"] == ["Cryptography"]


def test_get_team_member_not_found(api_client: TestClient) -> None:
    _register_test_user(api_client)

    response = api_client.get(f"/api/v1/team-members/{uuid4()}")
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_update_team_member(api_client: TestClient) -> None:
    user = _register_test_user(api_client)
    created = _create_team_member(
        api_client,
        name="Lisa Simpson",
        skills=["Cartooning", "Baking", "Skating", "Python"],
        user_id=user["id"],
    )

    response = api_client.put(
        f"/api/v1/team-members/{created['id']}",
        json={
            "name": "Lisa Manobal",
            "skills": ["Cartooning", "Baking", "Skating", "Python", "AI"],
        },
    )
    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["id"] == created["id"]
    assert body["name"] == "Lisa Manobal"
    assert body["skills"] == ["Cartooning", "Baking", "Skating", "Python", "AI"]


def test_update_team_member_not_found(api_client: TestClient) -> None:
    _register_test_user(api_client)

    response = api_client.put(
        f"/api/v1/team-members/{uuid4()}",
        json={
            "name": "Lisa Manobal",
            "skills": ["Cartooning", "Baking", "Skating", "Python", "AI"],
        },
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_delete_team_member(api_client: TestClient) -> None:
    user = _register_test_user(api_client)
    created = _create_team_member(
        api_client,
        name="Jennie Kim",
        skills=["K-Pop", "Dancing", "Singing", "Rapping"],
        user_id=user["id"],
    )

    member_id = created["id"]
    response = api_client.delete(f"/api/v1/team-members/{member_id}")
    assert response.status_code == status.HTTP_204_NO_CONTENT

    response = api_client.get(f"/api/v1/team-members/{member_id}")
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_delete_team_member_not_found(api_client: TestClient) -> None:
    _register_test_user(api_client)
    response = api_client.delete(f"/api/v1/team-members/{uuid4()}")
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_delete_team_member_conflict(api_client: TestClient) -> None:
    register_response = _register_test_user(api_client)
    created = _create_team_member(
        api_client,
        name="Roseanne Park",
        skills=["K-Pop", "Dancing", "Singing", "Rapping"],
        user_id=register_response["id"],
    )

    member_id = created["id"]
    _insert_assigned_task(
        member_id=member_id,
        created_by_id=register_response["id"],
    )

    response = api_client.delete(f"/api/v1/team-members/{member_id}")
    assert response.status_code == status.HTTP_409_CONFLICT


def test_update_team_member_validation_error(api_client: TestClient) -> None:
    _register_test_user(api_client)
    response = api_client.put(f"/api/v1/team-members/{uuid4()}", json={"name": None})
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_update_team_member_clears_skills(api_client: TestClient) -> None:
    user = _register_test_user(api_client)
    created = _create_team_member(
        api_client,
        name="Jisoo Kim",
        skills=["K-Pop", "Dancing", "Singing", "Rapping"],
        user_id=user["id"],
    )

    member_id = created["id"]
    response = api_client.put(f"/api/v1/team-members/{member_id}", json={"skills": []})
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["skills"] == []


def test_create_team_member_missing_user_returns_404(api_client: TestClient) -> None:
    _register_test_user(api_client)
    response = api_client.post(
        "/api/v1/team-members/",
        json={
            "name": "Kim Nanjoon",
            "skills": ["K-Pop", "Dancing", "Singing", "Rapping"],
            "user_id": str(uuid4()),
        },
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_create_team_member_duplicate_user_returns_409(api_client: TestClient) -> None:
    user = _register_test_user(api_client)
    _create_team_member(
        api_client,
        name="Son Heung Min",
        skills=["Football", "Shooting", "Passing", "Heading"],
        user_id=user["id"],
    )
    response = api_client.post(
        "/api/v1/team-members/",
        json={
            "name": "Son Heung Min",
            "skills": ["Football", "Shooting", "Passing", "Heading"],
            "user_id": user["id"],
        },
    )
    assert response.status_code == status.HTTP_409_CONFLICT


def test_create_task_with_linked_team_member_succeeds(
    api_client: TestClient,
) -> None:
    user = _register_test_user(api_client)
    team_member = _create_team_member(
        api_client,
        name="Min Yoongi",
        skills=["Producing", "Rapping"],
        user_id=user["id"],
    )

    response = api_client.post(
        "/api/v1/tasks/",
        json={
            "title": "Write project kickoff plan",
            "assignee_id": team_member["id"],
        },
    )

    assert response.status_code == status.HTTP_201_CREATED
    body = response.json()
    assert body["assignee_id"] == team_member["id"]
    assert body["created_by_id"] == user["id"]
