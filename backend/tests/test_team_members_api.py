from uuid import uuid4

from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from app.core.config import settings


def _register_test_user(api_client: TestClient) -> dict:
    response = api_client.post(
        "/api/v1/auth/register",
        json={
            "email": f"ada.lovelace{uuid4()}@example.com",
            "password": "ada_lovelace_password",
            "name": "Ada Lovelace",
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
    _register_test_user(api_client)
    response = api_client.post(
        "/api/v1/team-members/",
        json={
            "name": "Ada Lovelace",
            "skills": ["Python", "SQL", "Data Analysis", "AI"],
        },
    )
    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["name"] == "Ada Lovelace"
    assert response.json()["skills"] == ["Python", "SQL", "Data Analysis", "AI"]


def _create_team_member(
    api_client: TestClient, *, name: str, skills: list[str]
) -> dict:
    response = api_client.post(
        "/api/v1/team-members/",
        json={"name": name, "skills": skills},
    )
    assert response.status_code == status.HTTP_201_CREATED
    return response.json()


def test_get_team_members(api_client: TestClient) -> None:
    _register_test_user(api_client)
    created = _create_team_member(
        api_client,
        name="Grace Hopper",
        skills=["COBOL", "Compilers"],
    )

    response = api_client.get("/api/v1/team-members/")
    assert response.status_code == status.HTTP_200_OK
    members = response.json()
    match = next(m for m in members if m["id"] == created["id"])
    assert match["name"] == "Grace Hopper"
    assert match["skills"] == ["COBOL", "Compilers"]


def test_get_team_member(api_client: TestClient) -> None:
    _register_test_user(api_client)
    created = _create_team_member(
        api_client,
        name="Alan Turing",
        skills=["Cryptography"],
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
    _register_test_user(api_client)
    created = _create_team_member(
        api_client,
        name="Lisa Simpson",
        skills=["Cartooning", "Baking", "Skating", "Python"],
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
    _register_test_user(api_client)
    created = api_client.post(
        "/api/v1/team-members/",
        json={
            "name": "Jennie Kim",
            "skills": ["K-Pop", "Dancing", "Singing", "Rapping"],
        },
    )
    assert created.status_code == status.HTTP_201_CREATED
    assert created.json()["name"] == "Jennie Kim"
    assert created.json()["skills"] == ["K-Pop", "Dancing", "Singing", "Rapping"]

    member_id = created.json()["id"]
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
    created = api_client.post(
        "/api/v1/team-members/",
        json={
            "name": "Roseanne Park",
            "skills": ["K-Pop", "Dancing", "Singing", "Rapping"],
        },
    )
    assert created.status_code == status.HTTP_201_CREATED
    assert created.json()["name"] == "Roseanne Park"
    assert created.json()["skills"] == ["K-Pop", "Dancing", "Singing", "Rapping"]

    member_id = created.json()["id"]
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
    _register_test_user(api_client)
    created = api_client.post(
        "/api/v1/team-members/",
        json={
            "name": "Jisoo Kim",
            "skills": ["K-Pop", "Dancing", "Singing", "Rapping"],
        },
    )
    assert created.status_code == status.HTTP_201_CREATED
    assert created.json()["name"] == "Jisoo Kim"
    assert created.json()["skills"] == ["K-Pop", "Dancing", "Singing", "Rapping"]

    member_id = created.json()["id"]
    response = api_client.put(f"/api/v1/team-members/{member_id}", json={"skills": []})
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["skills"] == []
