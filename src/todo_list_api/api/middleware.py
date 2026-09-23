import logging

from fastapi import Request, Response, status

from todo_list_api.api.errors import message_response

logger = logging.getLogger(__name__)

EXEMPT_PATHS = frozenset({"/health", "/docs", "/redoc", "/openapi.json"})
UNKNOWN_CLIENT = "unknown"


def client_key(request: Request) -> str:
    return request.client.host if request.client else UNKNOWN_CLIENT


async def rate_limit_middleware(request: Request, call_next) -> Response:
    if request.url.path in EXEMPT_PATHS:
        return await call_next(request)

    decision = await request.app.state.rate_limiter.acquire(client_key(request))

    if decision.allowed:
        return await call_next(request)

    logger.warning("stressed out: rate limit hit by %s", client_key(request))
    response = message_response(
        status.HTTP_429_TOO_MANY_REQUESTS,
        "Too Many Requests",
    )
    response.headers["Retry-After"] = str(decision.retry_after_seconds)
    return response
