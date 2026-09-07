"""Shared response envelopes."""
from typing import Generic, List, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    items: List[T]
    total: int
    limit: int
    offset: int


class Message(BaseModel):
    message: str


class HealthOut(BaseModel):
    status: str = Field(examples=["ok"])
    database: str = Field(examples=["reachable"])
    environment: str
