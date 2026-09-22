import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from todo_list_api.db.base import Base
from todo_list_api.db.models import Todo, User

pytestmark = pytest.mark.anyio


def build_user(email: str) -> User:
    return User(name="Max", email=email, password_hash="not-a-real-hash")


async def test_migrations_match_models(engine: AsyncEngine) -> None:
    async with engine.connect() as connection:
        diff = await connection.run_sync(
            lambda sync_connection: compare_metadata(
                MigrationContext.configure(
                    sync_connection, opts={"compare_type": True}
                ),
                Base.metadata,
            )
        )

    assert diff == []


async def test_email_uniqueness_ignores_case(session: AsyncSession) -> None:
    session.add(build_user("max@pitwall.com"))
    await session.flush()

    session.add(build_user("MAX@PitWall.com"))

    with pytest.raises(IntegrityError):
        await session.flush()


async def test_todo_defaults_are_applied_by_the_database(
    session: AsyncSession,
) -> None:
    user = build_user("lando@pitwall.com")
    session.add(user)
    await session.flush()

    todo = Todo(owner_id=user.id, title="Box this lap")
    session.add(todo)
    await session.flush()

    assert todo.description == ""
    assert todo.completed is False
    assert todo.created_at is not None
    assert todo.updated_at is not None


async def test_deleting_a_user_cascades_to_their_todos(
    session: AsyncSession,
) -> None:
    user = build_user("oscar@pitwall.com")
    session.add(user)
    await session.flush()
    session.add(Todo(owner_id=user.id, title="Switch to plan B"))
    await session.flush()

    await session.delete(user)
    await session.flush()

    remaining = await session.scalars(select(Todo).where(Todo.owner_id == user.id))

    assert remaining.all() == []
