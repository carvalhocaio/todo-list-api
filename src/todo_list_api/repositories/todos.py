from collections.abc import Sequence

from sqlalchemy import ColumnElement, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from todo_list_api.db.models import Todo
from todo_list_api.domain.pagination import Page, PageRequest
from todo_list_api.domain.todos import TodoFilter, TodoSort

LIKE_ESCAPE_CHAR = "\\"


def escape_like(term: str) -> str:
    for character in (LIKE_ESCAPE_CHAR, "%", "_"):
        term = term.replace(character, LIKE_ESCAPE_CHAR + character)
    return term


class SqlAlchemyTodoRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, todo: Todo) -> Todo:
        self._session.add(todo)
        await self._session.flush()
        return todo

    async def get(self, todo_id: int) -> Todo | None:
        return await self._session.get(Todo, todo_id)

    async def delete(self, todo: Todo) -> None:
        await self._session.delete(todo)
        await self._session.flush()

    async def list_for_owner(
        self,
        owner_id: int,
        *,
        filters: TodoFilter,
        sort: TodoSort,
        page_request: PageRequest,
    ) -> Page[Todo]:
        conditions = self._conditions(owner_id, filters)
        total = await self._session.scalar(
            select(func.count()).select_from(Todo).where(*conditions)
        )
        rows = await self._session.scalars(
            select(Todo)
            .where(*conditions)
            .order_by(*self._ordering(sort))
            .offset(page_request.offset)
            .limit(page_request.limit)
        )
        return Page(
            items=rows.all(),
            page=page_request.page,
            limit=page_request.limit,
            total=total or 0,
        )

    @staticmethod
    def _conditions(owner_id: int, filters: TodoFilter) -> list[ColumnElement[bool]]:
        conditions: list[ColumnElement[bool]] = [Todo.owner_id == owner_id]
        if filters.completed is not None:
            conditions.append(Todo.completed.is_(filters.completed))
        if filters.search:
            pattern = f"%{escape_like(filters.search)}%"
            conditions.append(
                or_(
                    Todo.title.ilike(pattern, escape=LIKE_ESCAPE_CHAR),
                    Todo.description.ilike(pattern, escape=LIKE_ESCAPE_CHAR),
                )
            )
        return conditions

    @staticmethod
    def _ordering(sort: TodoSort) -> Sequence[ColumnElement[object]]:
        column = getattr(Todo, sort.field.value)
        if sort.descending:
            return (column.desc(), Todo.id.desc())  # pyright: ignore[reportReturnType]
        return (column.asc(), Todo.id.asc())  # pyright: ignore[reportReturnType]
