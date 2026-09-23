from datetime import timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from todo_list_api.core.security import (
    AccessTokenCodec,
    PasswordHasher,
    RefreshTokenFactory,
)
from todo_list_api.domain.errors import (
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
    InvalidRefreshTokenError,
    RefreshTokenReusedError,
)
from todo_list_api.repositories.refresh_tokens import (
    SqlAlchemyRefreshTokenRepository,
)
from todo_list_api.repositories.users import SqlAlchemyUserRepository
from todo_list_api.services.auth import AuthService

pytestmark = pytest.mark.anyio

SECRET = "pit-wall-test-secret-with-plenty-of-entropy"
CREDENTIALS = {"email": "max@pitwall.com", "password": "box-box-box"}


@pytest.fixture(scope="module")
def hasher() -> PasswordHasher:
    return PasswordHasher()


@pytest.fixture
def service(session: AsyncSession, hasher: PasswordHasher) -> AuthService:
    return AuthService(
        users=SqlAlchemyUserRepository(session),
        refresh_tokens=SqlAlchemyRefreshTokenRepository(session),
        hasher=hasher,
        access_tokens=AccessTokenCodec(
            secret_key=SECRET,
            algorithm="HS256",
            issuer="pit-wall",
            ttl=timedelta(minutes=15),
        ),
        refresh_token_factory=RefreshTokenFactory(ttl=timedelta(days=7)),
    )


async def test_registration_returns_a_usable_token_pair(
    service: AuthService,
) -> None:
    pair = await service.register(name="Max", **CREDENTIALS)

    assert pair.access_token
    assert pair.refresh_token


async def test_duplicate_email_is_rejected_regardless_of_case(
    service: AuthService,
) -> None:
    await service.register(name="Max", **CREDENTIALS)

    with pytest.raises(EmailAlreadyRegisteredError):
        await service.register(
            name="Impostor",
            email="MAX@PitWall.com",
            password="another-password",
        )


async def test_login_succeeds_with_correct_credentials(
    service: AuthService,
) -> None:
    await service.register(name="Max", **CREDENTIALS)

    assert await service.login(**CREDENTIALS)


@pytest.mark.parametrize(
    "credentials",
    [
        {"email": "max@pitwall.com", "password": "wrong-password"},
        {"email": "ghost@pitwall.com", "password": "box-box-box"},
    ],
    ids=["wrong-password", "unknown-email"],
)
async def test_login_rejects_bad_credentials(
    service: AuthService, credentials: dict[str, str]
) -> None:
    await service.register(name="Max", **CREDENTIALS)

    with pytest.raises(InvalidCredentialsError):
        await service.login(**credentials)


async def test_refresh_rotates_the_token(service: AuthService) -> None:
    original = await service.register(name="Max", **CREDENTIALS)

    rotated = await service.refresh(original.refresh_token)

    assert rotated.refresh_token != original.refresh_token


async def test_reusing_a_rotated_token_revokes_the_whole_family(
    service: AuthService,
) -> None:
    original = await service.register(name="Max", **CREDENTIALS)
    rotated = await service.refresh(original.refresh_token)

    with pytest.raises(RefreshTokenReusedError):
        await service.refresh(original.refresh_token)

    with pytest.raises(InvalidRefreshTokenError):
        await service.refresh(rotated.refresh_token)


async def test_unknown_refresh_token_is_rejected(service: AuthService) -> None:
    with pytest.raises(InvalidRefreshTokenError):
        await service.refresh("never-issued")
