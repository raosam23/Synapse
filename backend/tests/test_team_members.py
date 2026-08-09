"""Tests for team members CRUD API."""

from uuid import uuid4

from fastapi.testclient import TestClient

from tests.conftest import TEAM_MEMBERS_URL


def test_create_team_member(client: TestClient, team_member_ids: list[str]):
    payload = {"name": f"Ada-{uuid4().hex[:8]}", "skills": ["python", "fastapi"]}
    response = client.post(f"{TEAM_MEMBERS_URL}/", json=payload)

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == payload["name"]
    assert body["skills"] == payload["skills"]
    assert "id" in body
    team_member_ids.append(body["id"])


def test_create_team_member_defaults_skills_to_empty_list(
    client: TestClient, team_member_ids: list[str]
):
    payload = {"name": f"NoSkills-{uuid4().hex[:8]}"}
    response = client.post(f"{TEAM_MEMBERS_URL}/", json=payload)

    assert response.status_code == 201
    body = response.json()
    assert body["skills"] == []
    team_member_ids.append(body["id"])


def test_create_team_member_rejects_empty_name(client: TestClient):
    response = client.post(f"{TEAM_MEMBERS_URL}/", json={"name": "", "skills": []})

    assert response.status_code == 422


def test_create_team_member_rejects_missing_name(client: TestClient):
    response = client.post(f"{TEAM_MEMBERS_URL}/", json={"skills": ["python"]})

    assert response.status_code == 422


def test_list_team_members(client: TestClient, team_member_ids: list[str]):
    name = f"ListMe-{uuid4().hex[:8]}"
    create = client.post(f"{TEAM_MEMBERS_URL}/", json={"name": name, "skills": ["go"]})
    assert create.status_code == 201
    member_id = create.json()["id"]
    team_member_ids.append(member_id)

    response = client.get(f"{TEAM_MEMBERS_URL}/")
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    assert any(item["id"] == member_id and item["name"] == name for item in body)


def test_get_team_member(client: TestClient, team_member_ids: list[str]):
    create = client.post(
        f"{TEAM_MEMBERS_URL}/",
        json={"name": f"GetMe-{uuid4().hex[:8]}", "skills": ["rust"]},
    )
    assert create.status_code == 201
    member = create.json()
    team_member_ids.append(member["id"])

    response = client.get(f"{TEAM_MEMBERS_URL}/{member['id']}")
    assert response.status_code == 200
    assert response.json() == member


def test_get_team_member_not_found(client: TestClient):
    missing_id = uuid4()
    response = client.get(f"{TEAM_MEMBERS_URL}/{missing_id}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Team member not found"


def test_update_team_member_name(client: TestClient, team_member_ids: list[str]):
    create = client.post(
        f"{TEAM_MEMBERS_URL}/",
        json={"name": f"Before-{uuid4().hex[:8]}", "skills": ["java"]},
    )
    assert create.status_code == 201
    member_id = create.json()["id"]
    team_member_ids.append(member_id)

    response = client.put(f"{TEAM_MEMBERS_URL}/{member_id}", json={"name": "JENNIE"})
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "JENNIE"
    assert body["skills"] == ["java"]


def test_update_team_member_clear_skills(
    client: TestClient, team_member_ids: list[str]
):
    create = client.post(
        f"{TEAM_MEMBERS_URL}/",
        json={"name": f"ClearSkills-{uuid4().hex[:8]}", "skills": ["python"]},
    )
    assert create.status_code == 201
    member_id = create.json()["id"]
    team_member_ids.append(member_id)

    response = client.put(f"{TEAM_MEMBERS_URL}/{member_id}", json={"skills": []})
    assert response.status_code == 200
    assert response.json()["skills"] == []


def test_update_team_member_rejects_empty_name(
    client: TestClient, team_member_ids: list[str]
):
    create = client.post(
        f"{TEAM_MEMBERS_URL}/",
        json={"name": f"KeepName-{uuid4().hex[:8]}", "skills": []},
    )
    assert create.status_code == 201
    member_id = create.json()["id"]
    team_member_ids.append(member_id)

    response = client.put(f"{TEAM_MEMBERS_URL}/{member_id}", json={"name": ""})
    assert response.status_code == 422


def test_update_team_member_not_found(client: TestClient):
    response = client.put(f"{TEAM_MEMBERS_URL}/{uuid4()}", json={"name": "Nope"})
    assert response.status_code == 404
    assert response.json()["detail"] == "Team member not found"


def test_delete_team_member(client: TestClient):
    create = client.post(
        f"{TEAM_MEMBERS_URL}/",
        json={"name": f"DeleteMe-{uuid4().hex[:8]}", "skills": []},
    )
    assert create.status_code == 201
    member_id = create.json()["id"]

    delete = client.delete(f"{TEAM_MEMBERS_URL}/{member_id}")
    assert delete.status_code == 204

    get_after = client.get(f"{TEAM_MEMBERS_URL}/{member_id}")
    assert get_after.status_code == 404


def test_delete_team_member_not_found(client: TestClient):
    response = client.delete(f"{TEAM_MEMBERS_URL}/{uuid4()}")
    assert response.status_code == 404
    assert response.json()["detail"] == "Team member not found"
