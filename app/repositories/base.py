"""Thin generic repository. Keeps SQLAlchemy out of the service layer."""
from typing import Any, Generic, List, Optional, Sequence, Type, TypeVar

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    def __init__(self, model: Type[ModelT], db: Session):
        self.model = model
        self.db = db

    def get(self, pk: Any) -> Optional[ModelT]:
        return self.db.get(self.model, pk)

    def list(self, limit: int = 50, offset: int = 0, **filters: Any) -> Sequence[ModelT]:
        stmt = select(self.model)
        for field, value in filters.items():
            if value is not None and hasattr(self.model, field):
                stmt = stmt.where(getattr(self.model, field) == value)
        return self.db.execute(stmt.limit(limit).offset(offset)).scalars().all()

    def count(self, **filters: Any) -> int:
        stmt = select(func.count()).select_from(self.model)
        for field, value in filters.items():
            if value is not None and hasattr(self.model, field):
                stmt = stmt.where(getattr(self.model, field) == value)
        return int(self.db.execute(stmt).scalar_one())

    def add(self, obj: ModelT) -> ModelT:
        self.db.add(obj)
        self.db.flush()
        return obj

    def delete(self, obj: ModelT) -> None:
        self.db.delete(obj)
        self.db.flush()

    def bulk_add(self, objs: List[ModelT]) -> int:
        self.db.add_all(objs)
        self.db.flush()
        return len(objs)
