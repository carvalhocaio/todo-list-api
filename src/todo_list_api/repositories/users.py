from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from todo_list_api.db.models import User


class SqlAlchemyUserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, user: User) -> User:
        self._session.add(user)
        await self._session.flush()
        return user

    async def get(self, user_id: int) -> User | None:
        return await self._session.get(User, user_id)

    async def get_by_email(self, email: str) -> User | None:
        return await self._session.scalar(select(User).where(User.email == email))
