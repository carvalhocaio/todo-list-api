from todo_list_api.db.models import Todo
from todo_list_api.domain.errors import NotTodoOwnerError, TodoNotFoundError
from todo_list_api.domain.pagination import Page, PageRequest
from todo_list_api.domain.todos import TodoDraft, TodoFilter, TodoPatch, TodoSort
from todo_list_api.repositories.protocols import TodoRepository


class TodoService:
    def __init__(self, todos: TodoRepository) -> None:
        self._todos = todos

    async def create(self, owner_id: int, draft: TodoDraft) -> Todo:
        return await self._todos.add(
            Todo(
                owner_id=owner_id,
                title=draft.title,
                description=draft.description,
            )
        )

    async def update(self, todo_id: int, owner_id: int, patch: TodoPatch) -> Todo:
        todo = await self._owned(todo_id, owner_id)

        if patch.title is not None:
            todo.title = patch.title
        if patch.description is not None:
            todo.description = patch.description
        if patch.completed is not None:
            todo.completed = patch.completed

        return todo

    async def delete(self, todo_id: int, owner_id: int) -> None:
        await self._todos.delete(await self._owned(todo_id, owner_id))

    async def list_for_owner(
        self,
        owner_id: int,
        *,
        filters: TodoFilter,
        sort: TodoSort,
        page_request: PageRequest,
    ) -> Page[Todo]:
        return await self._todos.list_for_owner(
            owner_id,
            filters=filters,
            sort=sort,
            page_request=page_request,
        )

    async def _owned(self, todo_id: int, owner_id: int) -> Todo:
        todo = await self._todos.get(todo_id)

        if todo is None:
            raise TodoNotFoundError
        if todo.owner_id != owner_id:
            raise NotTodoOwnerError

        return todo
