"""通用分页模型。"""

from typing import TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class Page[T](BaseModel):
    total: int
    items: list[T]
