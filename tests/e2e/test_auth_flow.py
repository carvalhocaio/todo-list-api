import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.anyio

CREDENTIALS = {"email": "max@pitwall.com", "password": "box-box-box"}
REGISTRATION = {"name": "Max", **CREDENTIALS}


async def test_register_returns_201_with_a_token(client: AsyncClient) -> None:
    response = await client.post("/register", json=REGISTRATION)

    assert response.status_code == 201
    assert response.json()["token"]
    assert response.json()["refresh_token"]


async def test_duplicate_registration_returns_409(client: AsyncClient) -> None:
    await client.post("/register", json=REGISTRATION)

    response = await client.post("/register", json=REGISTRATION)

    assert response.status_code == 409
    assert response.json() == {"message": "Email already registered"}


async def test_login_returns_a_token(client: AsyncClient) -> None:
    await client.post("/register", json=REGISTRATION)

    response = await client.post("/login", json=CREDENTIALS)

    assert response.status_code == 200
    assert response.json()["token"]


async def test_login_with_wrong_password_returns_401(client: AsyncClient) -> None:
    await client.post("/register", json=REGISTRATION)

    response = await client.post("/login", json={**CREDENTIALS, "password": "stay-out"})

    assert response.status_code == 401
    assert response.json() == {"message": "Invalid credentials"}


async def test_refresh_rotates_and_detects_reuse(client: AsyncClient) -> None:
    registered = (await client.post("/register", json=REGISTRATION)).json()

    rotated = await client.post(
        "/refresh", json={"refresh_token": registered["refresh_token"]}
    )
    reused = await client.post(
        "/refresh", json={"refresh_token": registered["refresh_token"]}
    )
    revoked = await client.post(
        "/refresh", json={"refresh_token": rotated.json()["refresh_token"]}
    )

    assert rotated.status_code == 200
    assert reused.status_code == 401
    assert revoked.status_code == 401


async def test_invalid_payload_returns_422_with_field_errors(
    client: AsyncClient,
) -> None:
    response = await client.post(
        "/register", json={"name": "Max", "email": "not-an-email", "password": "short"}
    )

    assert response.status_code == 422
    assert response.json()["message"] == "Validation failed"
    assert {error["field"] for error in response.json()["errors"]} == {
        "email",
        "password",
    }
