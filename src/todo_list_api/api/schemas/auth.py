from pydantic import BaseModel, ConfigDict, EmailStr, Field, SecretStr

from todo_list_api.domain.auth import TokenPair

MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_LENGTH = 128


class RegisterRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=100)
    email: EmailStr = Field(max_length=254)
    password: SecretStr = Field(
        min_length=MIN_PASSWORD_LENGTH,
        max_length=MAX_PASSWORD_LENGTH,
    )


class LoginRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    email: EmailStr = Field(max_length=254)
    password: SecretStr = Field(max_length=MAX_PASSWORD_LENGTH)


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=1)


class TokenResponse(BaseModel):
    token: str
    refresh_token: str
    token_type: str = "bearer"  # noqa: S105

    @classmethod
    def from_pair(cls, pair: TokenPair) -> "TokenResponse":
        return cls(token=pair.access_token, refresh_token=pair.refresh_token)
