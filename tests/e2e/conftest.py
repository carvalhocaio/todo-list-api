from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import PostgresDsn, SecretStr
from sqlalchemy.ext.asyncio import AsyncSession

from todo_list_api.core.settings import Settings
from todo_list_api.main import create_app

BASE_URL = "http://pitwall.test"
TEST_SECRET = "pit-wall-e2e-secret-with-plenty-of-entropy"


@pytest.fixture
def settings(migrated_database_url: str) -> Settings:
    return Settings(
        database_url=PostgresDsn(migrated_database_url),
        jwt_secret_key=SecretStr(TEST_SECRET),
        rate_limit_capacity=1000,
        rate_limit_refill_per_second=1000.0,
    )


@pytest.fixture
async def client(
    settings: Settings, session: AsyncSession
) -> AsyncIterator[AsyncClient]:
    app = create_app(settings)
    app.state.session_factory = lambda: SharedSession(session)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url=BASE_URL,
    ) as client:
        yield client


class SharedSession:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def __aenter__(self) -> AsyncSession:
        return self._session

    async def __aexit__(self, *exc_info: object) -> None:
        return None
