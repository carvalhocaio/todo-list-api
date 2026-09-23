import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from todo_list_api.db.models import Todo, User
from todo_list_api.domain.pagination import PageRequest
from todo_list_api.domain.todos import TodoFilter, TodoSort, TodoSortField
from todo_list_api.repositories.todos import SqlAlchemyTodoRepository

pytestmark = pytest.mark.anyio


async def make_owner(session: AsyncSession, email: str) -> User:
    user = User(name="Race Engineer", email=email, password_hash="hash")
    session.add(user)
    await session.flush()
    return user


async def seed_todos(session: AsyncSession, owner_id: int) -> None:
    session.add_all(
        [
            Todo(owner_id=owner_id, title="Box this lap", completed=True),
            Todo(owner_id=owner_id, title="Switch to plan B", description="mediums"),
            Todo(owner_id=owner_id, title="Check tyre deg", description="100% wear"),
        ]
    )
    await session.flush()


@pytest.fixture
async def repository(session: AsyncSession) -> SqlAlchemyTodoRepository:
    return SqlAlchemyTodoRepository(session)


async def test_listing_is_scoped_to_the_owner(
    session: AsyncSession, repository: SqlAlchemyTodoRepository
) -> None:
    owner = await make_owner(session, "owner@pitwall.com")
    intruder = await make_owner(session, "intruder@pitwall.com")
    await seed_todos(session, owner.id)
    await seed_todos(session, intruder.id)

    page = await repository.list_for_owner(
        owner.id,
        filters=TodoFilter(),
        sort=TodoSort(),
        page_request=PageRequest(),
    )

    assert page.total == 3
    assert {todo.owner_id for todo in page.items} == {owner.id}


async def test_pagination_reports_total_beyond_the_page(
    session: AsyncSession, repository: SqlAlchemyTodoRepository
) -> None:
    owner = await make_owner(session, "pagination@pitwall.com")
    await seed_todos(session, owner.id)

    page = await repository.list_for_owner(
        owner.id,
        filters=TodoFilter(),
        sort=TodoSort(),
        page_request=PageRequest(page=2, limit=2),
    )

    assert page.total == 3
    assert len(page.items) == 1


async def test_completed_filter_narrows_results(
    session: AsyncSession, repository: SqlAlchemyTodoRepository
) -> None:
    owner = await make_owner(session, "filter@pitwall.com")
    await seed_todos(session, owner.id)

    page = await repository.list_for_owner(
        owner.id,
        filters=TodoFilter(completed=True),
        sort=TodoSort(),
        page_request=PageRequest(),
    )

    assert [todo.title for todo in page.items] == ["Box this lap"]


async def test_search_matches_title_and_description_case_insensitively(
    session: AsyncSession, repository: SqlAlchemyTodoRepository
) -> None:
    owner = await make_owner(session, "search@pitwall.com")
    await seed_todos(session, owner.id)

    page = await repository.list_for_owner(
        owner.id,
        filters=TodoFilter(search="MEDIUMS"),
        sort=TodoSort(),
        page_request=PageRequest(),
    )

    assert [todo.title for todo in page.items] == ["Switch to plan B"]


async def test_search_treats_wildcards_as_literals(
    session: AsyncSession, repository: SqlAlchemyTodoRepository
) -> None:
    owner = await make_owner(session, "wildcard@pitwall.com")
    await seed_todos(session, owner.id)

    page = await repository.list_for_owner(
        owner.id,
        filters=TodoFilter(search="100%"),
        sort=TodoSort(),
        page_request=PageRequest(),
    )

    assert page.total == 1


async def test_sorting_by_title_is_ascending_when_requested(
    session: AsyncSession, repository: SqlAlchemyTodoRepository
) -> None:
    owner = await make_owner(session, "sort@pitwall.com")
    await seed_todos(session, owner.id)

    page = await repository.list_for_owner(
        owner.id,
        filters=TodoFilter(),
        sort=TodoSort(field=TodoSortField.TITLE, descending=False),
        page_request=PageRequest(),
    )

    assert [todo.title for todo in page.items] == [
        "Box this lap",
        "Check tyre deg",
        "Switch to plan B",
    ]
