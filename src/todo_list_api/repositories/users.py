from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from todo_list_api.db.models import User
from todo_list_api.domain.errors import EmailAlreadyRegisteredError

UNIQUE_EMAIL_CONSTRAINT = "uq_users_email"


class SqlAlchemyUserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, user: User) -> User:
        try:
            async with self._session.begin_nested():
                self._session.add(user)
        except IntegrityError as error:
            if UNIQUE_EMAIL_CONSTRAINT in str(error.orig):
                raise EmailAlreadyRegisteredError from error
            raise
        return user

    async def get(self, user_id: int) -> User | None:
        return await self._session.get(User, user_id)

    async def get_by_email(self, email: str) -> User | None:
        return await self._session.scalar(select(User).where(User.email == email))
