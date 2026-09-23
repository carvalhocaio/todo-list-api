from typing import Annotated

from fastapi import APIRouter, Query, Response, status

from todo_list_api.api.dependencies import CurrentUserDep, TodoServiceDep
from todo_list_api.api.schemas.todos import (
    TodoCreateRequest,
    TodoPageResponse,
    TodoResponse,
    TodoSortOption,
    TodoUpdateRequest,
)
from todo_list_api.domain.pagination import MAX_PAGE_LIMIT, PageRequest
from todo_list_api.domain.todos import TodoDraft, TodoFilter, TodoPatch

router = APIRouter(prefix="/todos", tags=["todos"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_todo(
    payload: TodoCreateRequest,
    service: TodoServiceDep,
    current_user: CurrentUserDep,
) -> TodoResponse:
    todo = await service.create(
        current_user.id,
        TodoDraft(title=payload.title, description=payload.description),
    )
    return TodoResponse.model_validate(todo)


@router.get("")
async def list_todos(
    service: TodoServiceDep,
    current_user: CurrentUserDep,
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=MAX_PAGE_LIMIT)] = 10,
    completed: bool | None = None,
    search: Annotated[str | None, Query(max_length=200)] = None,
    sort: TodoSortOption = TodoSortOption.CREATED_AT_DESC,
) -> TodoPageResponse:
    page_result = await service.list_for_owner(
        current_user.id,
        filters=TodoFilter(completed=completed, search=search),
        sort=sort.to_domain(),
        page_request=PageRequest(page=page, limit=limit),
    )
    return TodoPageResponse.from_page(page_result)


@router.put("/{todo_id}")
async def update_todo(
    todo_id: int,
    payload: TodoUpdateRequest,
    service: TodoServiceDep,
    current_user: CurrentUserDep,
) -> TodoResponse:
    todo = await service.update(
        todo_id,
        current_user.id,
        TodoPatch(
            title=payload.title,
            description=payload.description,
            completed=payload.completed,
        ),
    )
    return TodoResponse.model_validate(todo)


@router.delete("/{todo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_todo(
    todo_id: int,
    service: TodoServiceDep,
    current_user: CurrentUserDep,
) -> Response:
    await service.delete(todo_id, current_user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
