from typing import Any, Generic, TypeVar
from pydantic import BaseModel

T = TypeVar("T")

class PaginatedMeta(BaseModel):
    page: int
    page_size: int
    total: int
    total_pages: int = 0

    def model_post_init(self, __context: Any) -> None:
        if self.total_pages == 0:
            object.__setattr__(self, "total_pages", max(1, (self.total + self.page_size - 1) // self.page_size))


class APIResponse(BaseModel, Generic[T]):  # noqa: N801
    success: bool = True
    data: T | None = None
    message: str | None = None
    meta: Any | None = None


class PaginatedResponse(BaseModel, Generic[T]):
    success: bool = True
    data: list[T]
    meta: dict[str, Any]


class ErrorDetail(BaseModel):
    field: str | None = None
    issue: str


class ErrorResponse(BaseModel):
    success: bool = False
    error: dict[str, Any]
    request_id: str | None = None


# Lowercase alias for consistency across endpoint files
ApiResponse = APIResponse


def paginated(items: list, total: int, page: int, per_page: int) -> dict:
    return {
        "data": items,
        "meta": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "total_pages": (total + per_page - 1) // per_page,
        },
    }
