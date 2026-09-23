import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from todo_list_api.db.models import User
from todo_list_api.domain.errors import NotTodoOwnerError, TodoNotFoundError
from todo_list_api.domain.pagination import PageRequest
from todo_list_api.domain.todos import TodoDraft, TodoFilter, TodoPatch, TodoSort
from todo_list_api.repositories.todos import SqlAlchemyTodoRepository
from todo_list_api.services.todos import TodoService

pytestmark = pytest.mark.anyio


@pytest.fixture
def service(session: AsyncSession) -> TodoService:
    return TodoService(SqlAlchemyTodoRepository(session))


async def make_user(session: AsyncSession, email: str) -> User:
    user = User(name="Race Engineer", email=email, password_hash="hash")
    session.add(user)
    await session.flush()
    return user


async def test_created_todo_belongs_to_its_owner(
    session: AsyncSession, service: TodoService
) -> None:
    owner = await make_user(session, "owner@pitwall.com")

    todo = await service.create(owner.id, TodoDraft(title="Box this lap"))

    assert todo.id is not None
    assert todo.owner_id == owner.id
    assert todo.completed is False


async def test_update_changes_only_the_provided_fields(
    session: AsyncSession, service: TodoService
) -> None:
    owner = await make_user(session, "patch@pitwall.com")
    todo = await service.create(
        owner.id, TodoDraft(title="Box this lap", description="softs")
    )

    updated = await service.update(todo.id, owner.id, TodoPatch(completed=True))

    assert updated.title == "Box this lap"
    assert updated.description == "softs"
    assert updated.completed is True


async def test_updating_someone_elses_todo_is_forbidden(
    session: AsyncSession, service: TodoService
) -> None:
    owner = await make_user(session, "victim@pitwall.com")
    intruder = await make_user(session, "rival@pitwall.com")
    todo = await service.create(owner.id, TodoDraft(title="Undercut on lap 18"))

    with pytest.raises(NotTodoOwnerError):
        await service.update(todo.id, intruder.id, TodoPatch(title="Stay out"))


async def test_deleting_someone_elses_todo_is_forbidden(
    session: AsyncSession, service: TodoService
) -> None:
    owner = await make_user(session, "target@pitwall.com")
    intruder = await make_user(session, "thief@pitwall.com")
    todo = await service.create(owner.id, TodoDraft(title="Plan B"))

    with pytest.raises(NotTodoOwnerError):
        await service.delete(todo.id, intruder.id)


async def test_missing_todo_is_reported_as_not_found(
    session: AsyncSession, service: TodoService
) -> None:
    owner = await make_user(session, "empty@pitwall.com")

    with pytest.raises(TodoNotFoundError):
        await service.update(9999, owner.id, TodoPatch(title="Ghost"))


async def test_deleted_todo_disappears_from_the_listing(
    session: AsyncSession, service: TodoService
) -> None:
    owner = await make_user(session, "cleanup@pitwall.com")
    todo = await service.create(owner.id, TodoDraft(title="Retire the car"))

    await service.delete(todo.id, owner.id)
    page = await service.list_for_owner(
        owner.id,
        filters=TodoFilter(),
        sort=TodoSort(),
        page_request=PageRequest(),
    )

    assert page.total == 0
