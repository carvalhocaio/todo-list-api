from datetime import timedelta
from functools import lru_cache
from typing import Literal

from pydantic import Field, PositiveFloat, PositiveInt, PostgresDsn, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: PostgresDsn

    jwt_secret_key: SecretStr = Field(min_length=32)
    jwt_algorithm: Literal["HS256", "HS384", "HS512"] = "HS256"
    jwt_issuer: str = "pit-wall"
    access_token_ttl_minutes: PositiveInt = 15
    refresh_token_ttl_days: PositiveInt = 7

    rate_limit_capacity: PositiveInt = 20
    rate_limit_refill_per_second: PositiveFloat = 0.5

    @property
    def access_token_ttl(self) -> timedelta:
        return timedelta(minutes=self.access_token_ttl_minutes)

    @property
    def refresh_token_ttl(self) -> timedelta:
        return timedelta(days=self.refresh_token_ttl_days)


@lru_cache
def get_settings() -> Settings:
    return Settings()  # pyright: ignore[reportCallIssue]
