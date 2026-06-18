"""Data access repositories."""
from typing import Any, Generic, TypeVar

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import Base
from app.models.investigation import Investigation

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """Base repository with common CRUD operations."""

    def __init__(self, model: type[ModelType], session: AsyncSession):
        self.model = model
        self.session = session

    async def get(self, id: Any) -> ModelType | None:
        """Get a single record by ID."""
        result = await self.session.execute(
            select(self.model).where(self.model.id == id)
        )
        return result.scalar_one_or_none()

    async def get_multi(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
        filters: dict | None = None,
    ) -> list[ModelType]:
        """Get multiple records with pagination."""
        query = select(self.model)

        if filters:
            query = query.where(*[
                getattr(self.model, k) == v
                for k, v in filters.items()
                if hasattr(self.model, k)
            ])

        query = query.offset(skip).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def create(self, obj: ModelType) -> ModelType:
        """Create a new record."""
        self.session.add(obj)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj

    async def update(self, obj: ModelType, **kwargs: Any) -> ModelType:
        """Update a record."""
        for key, value in kwargs.items():
            if hasattr(obj, key):
                setattr(obj, key, value)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj

    async def delete(self, obj: ModelType) -> None:
        """Delete a record (soft delete if available)."""
        if hasattr(obj, "deleted_at"):
            obj.deleted_at = func.now()
        else:
            await self.session.delete(obj)
        await self.session.flush()

    async def count(self, filters: dict | None = None) -> int:
        """Count records matching filters."""
        query = select(func.count(self.model.id))

        if filters:
            query = query.where(*[
                getattr(self.model, k) == v
                for k, v in filters.items()
                if hasattr(self.model, k)
            ])

        result = await self.session.execute(query)
        return result.scalar_one()


class InvestigationRepository(BaseRepository[Investigation]):
    """Repository for investigation operations."""

    async def get_by_session(
        self,
        session_id: str,
        user_id: str | None = None,
    ) -> list[Investigation]:
        """Get all investigations for a session."""
        query = select(Investigation).where(
            Investigation.session_id == session_id
        ).order_by(Investigation.started_at.desc())

        if user_id:
            query = query.where(Investigation.user_id == user_id)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_recent(self, limit: int = 10) -> list[Investigation]:
        """Get recent investigations."""
        query = select(Investigation).order_by(
            Investigation.started_at.desc()
        ).limit(limit)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def search_similar(
        self,
        question: str,
        limit: int = 5,
    ) -> list[Investigation]:
        """Search for similar investigations by question."""
        # Use PostgreSQL full-text search if available
        query = select(Investigation).where(
            Investigation.question.ilike(f"%{question}%")
        ).order_by(Investigation.started_at.desc()).limit(limit)

        result = await self.session.execute(query)
        return list(result.scalars().all())
