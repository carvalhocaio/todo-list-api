import uuid
from typing import Protocol

from todo_list_api.db.models import RefreshToken, Todo, User
from todo_list_api.domain.pagination import Page, PageRequest
from todo_list_api.domain.todos import TodoFilter, TodoSort


class UserRepository(Protocol):
    async def add(self, user: User) -> User: ...

    async def get_by_email(self, email: str) -> User | None: ...

    async def get(self, user_id: int) -> User | None: ...


class TodoRepository(Protocol):
    async def add(self, todo: Todo) -> Todo: ...

    async def get(self, todo_id: int) -> Todo | None: ...

    async def delete(self, todo: Todo) -> None: ...

    async def list_for_owner(
        self,
        owner_id: int,
        *,
        filters: TodoFilter,
        sort: TodoSort,
        page_request: PageRequest,
    ) -> Page[Todo]: ...


class RefreshTokenRepository(Protocol):
    async def add(self, token: RefreshToken) -> RefreshToken: ...

    async def get_by_digest(self, digest: str) -> RefreshToken | None: ...

    async def mark_used(self, token: RefreshToken) -> None: ...

    async def revoke_family(self, family_id: uuid.UUID) -> None: ...
