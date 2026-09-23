import uuid

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from todo_list_api.core.clock import Clock, utc_now
from todo_list_api.db.models import RefreshToken


class SqlAlchemyRefreshTokenRepository:
    def __init__(self, session: AsyncSession, *, clock: Clock = utc_now) -> None:
        self._session = session
        self._clock = clock

    async def add(self, token: RefreshToken) -> RefreshToken:
        self._session.add(token)
        await self._session.flush()
        return token

    async def get_by_digest(self, digest: str) -> RefreshToken | None:
        return await self._session.scalar(
            select(RefreshToken).where(RefreshToken.digest == digest)
        )

    async def mark_used(self, token: RefreshToken) -> None:
        token.used_at = self._clock()
        await self._session.flush()

    async def revoke_family(self, family_id: uuid.UUID) -> None:
        await self._session.execute(
            update(RefreshToken)
            .where(
                RefreshToken.family_id == family_id,
                RefreshToken.revoked_at.is_(None),
            )
            .values(revoked_at=self._clock())
        )
        await self._session.flush()
