from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from todo_list_api.db.models import Todo
from todo_list_api.domain.pagination import Page
from todo_list_api.domain.todos import TodoSort, TodoSortField

MAX_TITLE_LENGTH = 200
MAX_DESCRIPTION_LENGTH = 2000


class TodoSortOption(StrEnum):
    CREATED_AT_DESC = "-created_at"
    CREATED_AT_ASC = "created_at"
    UPDATED_AT_DESC = "-updated_at"
    UPDATED_AT_ASC = "updated_at"
    TITLE_DESC = "-title"
    TITLE_ASC = "title"

    def to_domain(self) -> TodoSort:
        descending = self.value.startswith("-")
        return TodoSort(
            field=TodoSortField(self.value.lstrip("-")),
            descending=descending,
        )


class TodoCreateRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    title: str = Field(min_length=1, max_length=MAX_TITLE_LENGTH)
    description: str = Field(default="", max_length=MAX_DESCRIPTION_LENGTH)


class TodoUpdateRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    title: str | None = Field(default=None, min_length=1, max_length=MAX_TITLE_LENGTH)
    description: str | None = Field(default=None, max_length=MAX_DESCRIPTION_LENGTH)
    completed: bool | None = None


class TodoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str
    completed: bool
    created_at: datetime
    updated_at: datetime


class TodoPageResponse(BaseModel):
    data: list[TodoResponse]
    page: int
    limit: int
    total: int

    @classmethod
    def from_page(cls, page: Page[Todo]) -> "TodoPageResponse":
        return cls(
            data=[TodoResponse.model_validate(todo) for todo in page.items],
            page=page.page,
            limit=page.limit,
            total=page.total,
        )
