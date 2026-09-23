from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import PostgresDsn, SecretStr
from sqlalchemy.ext.asyncio import AsyncSession

from tests.e2e.conftest import BASE_URL, TEST_SECRET, SharedSession
from todo_list_api.core.settings import Settings
from todo_list_api.main import create_app

pytestmark = pytest.mark.anyio

CAPACITY = 3


@pytest.fixture
async def throttled_client(
    migrated_database_url: str, session: AsyncSession
) -> AsyncIterator[AsyncClient]:
    app = create_app(
        Settings(
            database_url=PostgresDsn(migrated_database_url),
            jwt_secret_key=SecretStr(TEST_SECRET),
            rate_limit_capacity=CAPACITY,
            rate_limit_refill_per_second=0.1,
        )
    )
    app.state.session_factory = lambda: SharedSession(session)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url=BASE_URL
    ) as client:
        yield client


async def test_requests_beyond_capacity_get_429_with_retry_after(
    throttled_client: AsyncClient,
) -> None:
    for _ in range(CAPACITY):
        await throttled_client.get("/todos")

    response = await throttled_client.get("/todos")

    assert response.status_code == 429
    assert response.json() == {"message": "Too Many Requests"}
    assert int(response.headers["retry-after"]) >= 1


async def test_health_endpoint_is_exempt_from_rate_limiting(
    throttled_client: AsyncClient,
) -> None:
    response = None
    for _ in range(CAPACITY + 5):
        response = await throttled_client.get("/health")

    assert response is not None
    assert response.status_code == 200
