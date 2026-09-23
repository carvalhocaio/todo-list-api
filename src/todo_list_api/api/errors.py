from collections.abc import Awaitable, Callable
from http import HTTPStatus

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from todo_list_api.domain.errors import (
    DomainError,
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
    InvalidRefreshTokenError,
    NotTodoOwnerError,
    TodoNotFoundError,
)

type ErrorHandler = Callable[[Request, Exception], Awaitable[JSONResponse]]

DOMAIN_ERROR_STATUS: dict[type[DomainError], int] = {
    EmailAlreadyRegisteredError: status.HTTP_409_CONFLICT,
    InvalidCredentialsError: status.HTTP_401_UNAUTHORIZED,
    InvalidRefreshTokenError: status.HTTP_401_UNAUTHORIZED,
    NotTodoOwnerError: status.HTTP_403_FORBIDDEN,
    TodoNotFoundError: status.HTTP_404_NOT_FOUND,
}

DOMAIN_ERROR_MESSAGE: dict[type[DomainError], str] = {
    EmailAlreadyRegisteredError: "Email already registered",
    InvalidCredentialsError: "Invalid credentials",
    InvalidRefreshTokenError: "Invalid refresh token",
}


def message_response(status_code: int, message: str) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"message": message})


def resolve_status(error: DomainError) -> int:
    for error_type, status_code in DOMAIN_ERROR_STATUS.items():
        if isinstance(error, error_type):
            return status_code
    return status.HTTP_400_BAD_REQUEST


def resolve_message(error: DomainError, status_code: int) -> str:
    for error_type, message in DOMAIN_ERROR_MESSAGE.items():
        if isinstance(error, error_type):
            return message
    return HTTPStatus(status_code).phrase


async def handle_domain_error(request: Request, error: Exception) -> JSONResponse:
    assert isinstance(error, DomainError)  # noqa: S101
    status_code = resolve_status(error)
    return message_response(status_code, resolve_message(error, status_code))


async def handle_http_exception(request: Request, error: Exception) -> JSONResponse:
    assert isinstance(error, HTTPException)  # noqa: S101
    detail = error.detail if isinstance(error.detail, str) else None
    response = message_response(
        error.status_code,
        detail or HTTPStatus(error.status_code).phrase,
    )
    response.headers.update(error.headers or {})
    return response


async def handle_validation_error(request: Request, error: Exception) -> JSONResponse:
    assert isinstance(error, RequestValidationError)  # noqa: S101
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={
            "message": "Validation failed",
            "errors": [
                {
                    "field": ".".join(str(part) for part in item["loc"][1:]),
                    "reason": item["msg"],
                }
                for item in error.errors()
            ],
        },
    )


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(DomainError, handle_domain_error)
    app.add_exception_handler(HTTPException, handle_http_exception)
    app.add_exception_handler(RequestValidationError, handle_validation_error)
