from fastapi import APIRouter, status

from todo_list_api.api.dependencies import AuthServiceDep
from todo_list_api.api.schemas.auth import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
)

router = APIRouter(tags=["auth"])


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, service: AuthServiceDep) -> TokenResponse:
    pair = await service.register(
        name=payload.name,
        email=payload.email,
        password=payload.password.get_secret_value(),
    )
    return TokenResponse.from_pair(pair)


@router.post("/login")
async def login(payload: LoginRequest, service: AuthServiceDep) -> TokenResponse:
    pair = await service.login(
        email=payload.email,
        password=payload.password.get_secret_value(),
    )
    return TokenResponse.from_pair(pair)


@router.post("/refresh")
async def refresh(payload: RefreshRequest, service: AuthServiceDep) -> TokenResponse:
    return TokenResponse.from_pair(await service.refresh(payload.refresh_token))
