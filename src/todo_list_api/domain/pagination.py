from collections.abc import Sequence
from dataclasses import dataclass

MAX_PAGE_LIMIT = 100


@dataclass(frozen=True, slots=True)
class PageRequest:
    page: int = 1
    limit: int = 10

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.limit


@dataclass(frozen=True, slots=True)
class Page[T]:
    items: Sequence[T]
    page: int
    limit: int
    total: int
