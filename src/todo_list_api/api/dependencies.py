from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from todo_list_api.core.security import InvalidAccessTokenError
from todo_list_api.db.models import User
from todo_list_api.repositories.refresh_tokens import SqlAlchemyRefreshTokenRepository
from todo_list_api.repositories.todos import SqlAlchemyTodoRepository
from todo_list_api.repositories.users import SqlAlchemyUserRepository
from todo_list_api.services.auth import AuthService
from todo_list_api.services.todos import TodoService

bearer_scheme = HTTPBearer(auto_error=False)

UNAUTHORIZED = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Unauthorized",
    headers={"WWW-Authenticate": "Bearer"},
)


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    async with request.app.state.session_factory() as session:
        yield session
        await session.commit()


SessionDep = Annotated[AsyncSession, Depends(get_session)]


def get_auth_service(request: Request, session: SessionDep) -> AuthService:
    state = request.app.state
    return AuthService(
        users=SqlAlchemyUserRepository(session),
        refresh_tokens=SqlAlchemyRefreshTokenRepository(session),
        hasher=state.password_hasher,
        access_tokens=state.access_tokens,
        refresh_token_factory=state.refresh_token_factory,
    )


def get_todo_service(session: SessionDep) -> TodoService:
    return TodoService(SqlAlchemyTodoRepository(session))


async def get_current_user(
    request: Request,
    session: SessionDep,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> User:
    if credentials is None:
        raise UNAUTHORIZED

    try:
        user_id = request.app.state.access_tokens.decode(credentials.credentials)
    except InvalidAccessTokenError as error:
        raise UNAUTHORIZED from error

    user = await SqlAlchemyUserRepository(session).get(user_id)

    if user is None:
        raise UNAUTHORIZED

    return user


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
TodoServiceDep = Annotated[TodoService, Depends(get_todo_service)]
CurrentUserDep = Annotated[User, Depends(get_current_user)]
