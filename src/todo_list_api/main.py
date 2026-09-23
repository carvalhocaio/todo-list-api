from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from todo_list_api.api.errors import register_error_handlers
from todo_list_api.api.middleware import rate_limit_middleware
from todo_list_api.api.rate_limit import TokenBucketRateLimiter
from todo_list_api.api.routers import auth, todos
from todo_list_api.core.security import (
    AccessTokenCodec,
    PasswordHasher,
    RefreshTokenFactory,
)
from todo_list_api.core.settings import Settings, get_settings
from todo_list_api.db.session import build_engine, build_session_factory

TITLE = "Pit Wall"
DESCRIPTION = "A to-do list API where every task is a strategy call."


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    engine = build_engine(str(app.state.settings.database_url))
    app.state.engine = engine
    app.state.session_factory = build_session_factory(engine)
    yield
    await engine.dispose()


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    app = FastAPI(
        title=TITLE,
        description=DESCRIPTION,
        version="0.1.0",
        lifespan=lifespan,
    )

    app.state.settings = settings
    app.state.password_hasher = PasswordHasher()
    app.state.access_tokens = AccessTokenCodec(
        secret_key=settings.jwt_secret_key.get_secret_value(),
        algorithm=settings.jwt_algorithm,
        issuer=settings.jwt_issuer,
        ttl=settings.access_token_ttl,
    )
    app.state.refresh_token_factory = RefreshTokenFactory(
        ttl=settings.refresh_token_ttl
    )
    app.state.rate_limiter = TokenBucketRateLimiter(
        capacity=settings.rate_limit_capacity,
        refill_per_second=settings.rate_limit_refill_per_second,
    )

    register_error_handlers(app)
    app.middleware("http")(rate_limit_middleware)
    app.include_router(auth.router)
    app.include_router(todos.router)

    @app.get("/health", tags=["ops"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
