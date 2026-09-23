import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.anyio

TODO = {"title": "Box this lap", "description": "softs"}


async def authenticate(client: AsyncClient, email: str) -> dict[str, str]:
    response = await client.post(
        "/register",
        json={"name": "Race Engineer", "email": email, "password": "box-box-box"},
    )
    return {"Authorization": f"Bearer {response.json()['token']}"}


async def test_full_todo_lifecycle(client: AsyncClient) -> None:
    headers = await authenticate(client, "owner@pitwall.com")

    created = await client.post("/todos", json=TODO, headers=headers)
    todo_id = created.json()["id"]
    updated = await client.put(
        f"/todos/{todo_id}", json={"completed": True}, headers=headers
    )
    deleted = await client.delete(f"/todos/{todo_id}", headers=headers)
    listed = await client.get("/todos", headers=headers)

    assert created.status_code == 201
    assert updated.json()["completed"] is True
    assert updated.json()["title"] == TODO["title"]
    assert deleted.status_code == 204
    assert listed.json()["total"] == 0


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("GET", "/todos"),
        ("POST", "/todos"),
        ("PUT", "/todos/1"),
        ("DELETE", "/todos/1"),
    ],
)
async def test_todo_endpoints_require_authentication(
    client: AsyncClient, method: str, path: str
) -> None:
    response = await client.request(method, path, json=TODO)

    assert response.status_code == 401
    assert response.json() == {"message": "Unauthorized"}
    assert response.headers["www-authenticate"] == "Bearer"


async def test_malformed_token_is_rejected(client: AsyncClient) -> None:
    response = await client.get("/todos", headers={"Authorization": "Bearer not-a-jwt"})

    assert response.status_code == 401


async def test_touching_another_users_todo_returns_403(client: AsyncClient) -> None:
    owner = await authenticate(client, "victim@pitwall.com")
    intruder = await authenticate(client, "rival@pitwall.com")
    todo_id = (await client.post("/todos", json=TODO, headers=owner)).json()["id"]

    updated = await client.put(
        f"/todos/{todo_id}", json={"title": "Stay out"}, headers=intruder
    )
    deleted = await client.delete(f"/todos/{todo_id}", headers=intruder)

    assert updated.status_code == 403
    assert updated.json() == {"message": "Forbidden"}
    assert deleted.status_code == 403


async def test_missing_todo_returns_404(client: AsyncClient) -> None:
    headers = await authenticate(client, "ghost@pitwall.com")

    response = await client.delete("/todos/9999", headers=headers)

    assert response.status_code == 404
    assert response.json() == {"message": "Not Found"}


async def test_listing_is_paginated_and_scoped_to_the_owner(
    client: AsyncClient,
) -> None:
    owner = await authenticate(client, "paginated@pitwall.com")
    intruder = await authenticate(client, "other@pitwall.com")
    for index in range(3):
        await client.post("/todos", json={"title": f"Lap {index}"}, headers=owner)
    await client.post("/todos", json={"title": "Not mine"}, headers=intruder)

    response = await client.get("/todos?page=2&limit=2", headers=owner)

    assert response.json()["total"] == 3
    assert response.json()["page"] == 2
    assert len(response.json()["data"]) == 1


async def test_filtering_and_sorting_are_applied(client: AsyncClient) -> None:
    headers = await authenticate(client, "filters@pitwall.com")
    await client.post("/todos", json={"title": "Alpha"}, headers=headers)
    beta_id = (
        await client.post("/todos", json={"title": "Beta"}, headers=headers)
    ).json()["id"]
    await client.put(f"/todos/{beta_id}", json={"completed": True}, headers=headers)

    completed = await client.get("/todos?completed=true", headers=headers)
    sorted_titles = await client.get("/todos?sort=title", headers=headers)
    searched = await client.get("/todos?search=alph", headers=headers)

    assert [todo["title"] for todo in completed.json()["data"]] == ["Beta"]
    assert [todo["title"] for todo in sorted_titles.json()["data"]] == [
        "Alpha",
        "Beta",
    ]
    assert searched.json()["total"] == 1


@pytest.mark.parametrize(
    "query",
    ["?page=0", "?limit=0", "?limit=101", "?sort=password_hash"],
)
async def test_invalid_query_parameters_are_rejected(
    client: AsyncClient, query: str
) -> None:
    headers = await authenticate(client, f"query{hash(query)}@pitwall.com")

    response = await client.get(f"/todos{query}", headers=headers)

    assert response.status_code == 422
