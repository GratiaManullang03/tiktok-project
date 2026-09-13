from typing import Generic, TypeVar, Optional, List
from pydantic import BaseModel

T = TypeVar("T")


class ResponseBase(BaseModel):
    success: bool
    message: str


class DataResponse(ResponseBase, Generic[T]):
    data: Optional[T] = None


class Pagination(BaseModel):
    page: int
    per_page: int
    total: int
    total_pages: int
    has_next: bool
    has_previous: bool


class PaginationResponse(ResponseBase, Generic[T]):
    data: List[T]
    pagination: Pagination

    @classmethod
    def build(
        cls,
        message: str,
        data: List[T],
        page: int,
        per_page: int,
        total: int,
    ) -> "PaginationResponse[T]":
        total_pages = (total + per_page - 1) // per_page if per_page else 0
        return cls(
            success=True,
            message=message,
            data=data,
            pagination=Pagination(
                page=page,
                per_page=per_page,
                total=total,
                total_pages=total_pages,
                has_next=page < total_pages,
                has_previous=page > 1,
            ),
        )
