import uuid
from datetime import timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from todo_list_api.core.clock import utc_now
from todo_list_api.db.models import RefreshToken, User
from todo_list_api.repositories.refresh_tokens import (
    SqlAlchemyRefreshTokenRepository,
)

pytestmark = pytest.mark.anyio


async def make_user(session: AsyncSession) -> User:
    user = User(name="Max", email=f"{uuid.uuid4()}@pitwall.com", password_hash="hash")
    session.add(user)
    await session.flush()
    return user


def make_token(user_id: int, family_id: uuid.UUID, digest: str) -> RefreshToken:
    return RefreshToken(
        user_id=user_id,
        family_id=family_id,
        digest=digest,
        expires_at=utc_now() + timedelta(days=7),
    )


async def test_token_is_retrievable_by_digest(session: AsyncSession) -> None:
    repository = SqlAlchemyRefreshTokenRepository(session)
    user = await make_user(session)
    await repository.add(make_token(user.id, uuid.uuid4(), "digest-one"))

    found = await repository.get_by_digest("digest-one")

    assert found is not None
    assert found.used_at is None
    assert found.revoked_at is None


async def test_marking_used_records_the_rotation(session: AsyncSession) -> None:
    repository = SqlAlchemyRefreshTokenRepository(session)
    user = await make_user(session)
    token = await repository.add(make_token(user.id, uuid.uuid4(), "digest-two"))

    await repository.mark_used(token)

    assert token.used_at is not None


async def test_revoking_a_family_leaves_other_families_untouched(
    session: AsyncSession,
) -> None:
    repository = SqlAlchemyRefreshTokenRepository(session)
    user = await make_user(session)
    compromised = uuid.uuid4()
    healthy = uuid.uuid4()
    await repository.add(make_token(user.id, compromised, "digest-three"))
    await repository.add(make_token(user.id, compromised, "digest-four"))
    await repository.add(make_token(user.id, healthy, "digest-five"))

    await repository.revoke_family(compromised)

    token_three = await repository.get_by_digest("digest-three")
    assert token_three is not None
    assert token_three.revoked_at is not None

    token_four = await repository.get_by_digest("digest-four")
    assert token_four is not None
    assert token_four.revoked_at is not None

    token_five = await repository.get_by_digest("digest-five")
    assert token_five is not None
    assert token_five.revoked_at is None
