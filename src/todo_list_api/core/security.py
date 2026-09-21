import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta

import jwt
from anyio import to_thread
from pwdlib import PasswordHash

from todo_list_api.core.clock import Clock, utc_now

REFRESH_TOKEN_BYTES = 32
REQUIRED_ACCESS_CLAIMS = ["sub", "iss", "iat", "exp"]


class InvalidAccessTokenError(Exception):
    pass


class PasswordHasher:
    def __init__(self) -> None:
        self._hasher = PasswordHash.recommended()
        self._decoy_hash = self._hasher.hash(secrets.token_urlsafe())

    async def hash(self, password: str) -> str:
        return await to_thread.run_sync(self._hasher.hash, password)

    async def verify(self, password: str, hashed: str | None) -> bool:
        if hashed is None:
            await to_thread.run_sync(self._hasher.verify, password, self._decoy_hash)
            return False
        return await to_thread.run_sync(self._hasher.verify, password, hashed)


class AccessTokenCodec:
    def __init__(
        self,
        *,
        secret_key: str,
        algorithm: str,
        issuer: str,
        ttl: timedelta,
        clock: Clock = utc_now,
    ) -> None:
        self._secret_key = secret_key
        self._algorithm = algorithm
        self._issuer = issuer
        self._ttl = ttl
        self._clock = clock

    def encode(self, user_id: int) -> str:
        issued_at = self._clock()
        payload = {
            "sub": str(user_id),
            "iss": self._issuer,
            "iat": issued_at,
            "exp": issued_at + self._ttl,
        }
        return jwt.encode(payload, self._secret_key, algorithm=self._algorithm)

    def decode(self, token: str) -> int:
        try:
            claims = jwt.decode(
                token,
                self._secret_key,
                algorithms=[self._algorithm],
                issuer=self._issuer,
                options={"require": REQUIRED_ACCESS_CLAIMS},
            )
        except jwt.PyJWTError as error:
            raise InvalidAccessTokenError from error
        return int(claims["sub"])


@dataclass(frozen=True, slots=True)
class IssuedRefreshToken:
    value: str
    digest: str
    expires_at: datetime


class RefreshTokenFactory:
    def __init__(self, *, ttl: timedelta, clock: Clock = utc_now) -> None:
        self._ttl = ttl
        self._clock = clock

    def issue(self) -> IssuedRefreshToken:
        value = secrets.token_urlsafe(REFRESH_TOKEN_BYTES)
        return IssuedRefreshToken(
            value=value,
            digest=self.digest(value),
            expires_at=self._clock() + self._ttl,
        )

    @staticmethod
    def digest(value: str) -> str:
        return hashlib.sha256(value.encode()).hexdigest()
