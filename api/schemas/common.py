from typing import Generic, List, TypeVar, Optional
from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginationMeta(BaseModel):
    page: int
    limit: int
    total: int
    total_pages: int
    has_next: bool
    has_prev: bool


class PaginatedResponse(BaseModel, Generic[T]):
    data: List[T] = Field(default_factory=list)  # type: ignore[assignment]
    pagination: PaginationMeta


def build_pagination(page: int, limit: int, total: int) -> PaginationMeta:
    total_pages = max(1, (total + limit - 1) // limit)
    return PaginationMeta(
        page=page,
        limit=limit,
        total=total,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_prev=page > 1,
    )
