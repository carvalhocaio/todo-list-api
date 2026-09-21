from datetime import timedelta

import pytest

from todo_list_api.core.clock import Clock, utc_now
from todo_list_api.core.security import (
    AccessTokenCodec,
    InvalidAccessTokenError,
    PasswordHasher,
    RefreshTokenFactory,
)

SECRET = "pit-wall-test-secret-with-plenty-of-entropy"
TTL = timedelta(minutes=15)


def make_codec(
    *,
    secret_key: str = SECRET,
    issuer: str = "pit-wall",
    clock: Clock = utc_now,
) -> AccessTokenCodec:
    return AccessTokenCodec(
        secret_key=secret_key,
        algorithm="HS256",
        issuer=issuer,
        ttl=TTL,
        clock=clock,
    )


@pytest.fixture(scope="module")
def hasher() -> PasswordHasher:
    return PasswordHasher()


@pytest.mark.anyio
async def test_password_hash_roundtrip(hasher: PasswordHasher) -> None:
    hashed = await hasher.hash("box-box-box")

    assert hashed != "box-box-box"
    assert await hasher.verify("box-box-box", hashed)
    assert not await hasher.verify("stay-out", hashed)


@pytest.mark.anyio
async def test_verify_without_stored_hash_fails(hasher: PasswordHasher) -> None:
    assert not await hasher.verify("box-box-box", None)


def test_access_token_roundtrip() -> None:
    codec = make_codec()

    assert codec.decode(codec.encode(44)) == 44


@pytest.mark.parametrize(
    "issuing_codec",
    [
        make_codec(clock=lambda: utc_now() - timedelta(days=1)),
        make_codec(issuer="dema"),
        make_codec(secret_key="another-secret-with-plenty-of-entropy"),
    ],
    ids=["expired", "foreign-issuer", "foreign-signature"],
)
def test_invalid_access_tokens_are_rejected(issuing_codec: AccessTokenCodec) -> None:
    token = issuing_codec.encode(44)

    with pytest.raises(InvalidAccessTokenError):
        make_codec().decode(token)


def test_malformed_access_token_is_rejected() -> None:
    with pytest.raises(InvalidAccessTokenError):
        make_codec().decode("not-a-jwt")


def test_refresh_token_is_stored_only_as_digest() -> None:
    issued = RefreshTokenFactory(ttl=timedelta(days=7)).issue()

    assert issued.value not in issued.digest
    assert RefreshTokenFactory.digest(issued.value) == issued.digest


def test_refresh_token_expiry_follows_clock() -> None:
    now = utc_now()
    factory = RefreshTokenFactory(ttl=timedelta(days=7), clock=lambda: now)

    assert factory.issue().expires_at == now + timedelta(days=7)
