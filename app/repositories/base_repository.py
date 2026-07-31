"""Generic CRUD repository shared by all concrete repositories."""

from typing import Generic, Type, TypeVar

from app.models import db

ModelType = TypeVar("ModelType", bound=db.Model)


class BaseRepository(Generic[ModelType]):
    """Generic data-access operations for a single SQLAlchemy model."""

    def __init__(self, model: Type[ModelType]) -> None:
        self.model = model

    def get_by_id(self, entity_id: int) -> ModelType | None:
        return db.session.get(self.model, entity_id)

    def get_all(self) -> list[ModelType]:
        return db.session.query(self.model).all()

    def add(self, entity: ModelType) -> ModelType:
        db.session.add(entity)
        db.session.commit()
        return entity

    def add_all(self, entities: list[ModelType]) -> list[ModelType]:
        db.session.add_all(entities)
        db.session.commit()
        return entities

    def delete(self, entity: ModelType) -> None:
        db.session.delete(entity)
        db.session.commit()

    def count(self) -> int:
        return db.session.query(self.model).count()
