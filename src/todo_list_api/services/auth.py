import uuid

from todo_list_api.core.clock import Clock, utc_now
from todo_list_api.core.security import (
    AccessTokenCodec,
    PasswordHasher,
    RefreshTokenFactory,
)
from todo_list_api.db.models import RefreshToken, User
from todo_list_api.domain.auth import TokenPair
from todo_list_api.domain.errors import (
    InvalidCredentialsError,
    InvalidRefreshTokenError,
    RefreshTokenReusedError,
)
from todo_list_api.repositories.protocols import (
    RefreshTokenRepository,
    UserRepository,
)


class AuthService:
    def __init__(
        self,
        *,
        users: UserRepository,
        refresh_tokens: RefreshTokenRepository,
        hasher: PasswordHasher,
        access_tokens: AccessTokenCodec,
        refresh_token_factory: RefreshTokenFactory,
        clock: Clock = utc_now,
    ) -> None:
        self._users = users
        self._refresh_tokens = refresh_tokens
        self._hasher = hasher
        self._access_tokens = access_tokens
        self._refresh_token_factory = refresh_token_factory
        self._clock = clock

    async def register(self, *, name: str, email: str, password: str) -> TokenPair:
        user = await self._users.add(
            User(
                name=name, email=email, password_hash=await self._hasher.hash(password)
            )
        )
        return await self._issue_pair(user.id, uuid.uuid4())

    async def login(self, *, email: str, password: str) -> TokenPair:
        user = await self._users.get_by_email(email)
        stored_hash = user.password_hash if user else None

        if not await self._hasher.verify(password, stored_hash) or user is None:
            raise InvalidCredentialsError

        return await self._issue_pair(user.id, uuid.uuid4())

    async def refresh(self, refresh_token: str) -> TokenPair:
        digest = RefreshTokenFactory.digest(refresh_token)
        stored = await self._refresh_tokens.get_by_digest(digest)

        if stored is None:
            raise InvalidRefreshTokenError

        if stored.used_at is not None:
            await self._refresh_tokens.revoke_family(stored.family_id)
            raise RefreshTokenReusedError

        if stored.revoked_at is not None or stored.expires_at <= self._clock():
            raise InvalidRefreshTokenError

        await self._refresh_tokens.mark_used(stored)
        return await self._issue_pair(stored.user_id, stored.family_id)

    async def _issue_pair(self, user_id: int, family_id: uuid.UUID) -> TokenPair:
        issued = self._refresh_token_factory.issue()
        await self._refresh_tokens.add(
            RefreshToken(
                user_id=user_id,
                family_id=family_id,
                digest=issued.digest,
                expires_at=issued.expires_at,
            )
        )
        return TokenPair(
            access_token=self._access_tokens.encode(user_id),
            refresh_token=issued.value,
        )
