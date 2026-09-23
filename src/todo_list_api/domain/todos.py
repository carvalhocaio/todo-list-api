from dataclasses import dataclass
from enum import StrEnum


class TodoSortField(StrEnum):
    CREATED_AT = "created_at"
    UPDATED_AT = "updated_at"
    TITLE = "title"


@dataclass(frozen=True, slots=True)
class TodoSort:
    field: TodoSortField = TodoSortField.CREATED_AT
    descending: bool = True


@dataclass(frozen=True, slots=True)
class TodoFilter:
    completed: bool | None = None
    search: str | None = None
