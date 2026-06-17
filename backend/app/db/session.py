"""Async database session management."""
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.config import settings


def get_engine(
    database_url: str | None = None,
    *,
    echo: bool | None = None,
    pool_size: int | None = None,
    max_overflow: int | None = None,
    use_null_pool: bool = False,
):
    """Create an async SQLAlchemy engine.

    Args:
        database_url: Optional override for database URL.
        echo: Optional override for SQL echo setting.
        pool_size: Optional override for pool size.
        max_overflow: Optional override for max overflow.
        use_null_pool: Use NullPool (useful for testing).
    """
    url = database_url or settings.DATABASE_URL
    pool_args: dict = {}

    if use_null_pool:
        pool_args["poolclass"] = NullPool
    else:
        pool_args["pool_size"] = pool_size or settings.DATABASE_POOL_SIZE
        pool_args["max_overflow"] = max_overflow or settings.DATABASE_MAX_OVERFLOW
        pool_args["pool_pre_ping"] = True  # Verify connections before use
        pool_args["pool_recycle"] = 3600   # Recycle connections every hour

    return create_async_engine(
        url,
        echo=echo if echo is not None else settings.DATABASE_ECHO,
        **pool_args,
    )


# Default engine for the application
engine = get_engine()

# Session factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for getting a database session.

    Usage:
        @router.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Initialize database by creating all tables.

    Should be called on application startup.
    For production, use Alembic migrations instead.
    """
    from app.db.base import Base  # noqa: F401
    # Import all models to register them
    from app.models import user, event, subscription, payment, investigation  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """Close all database connections.

    Should be called on application shutdown.
    """
    await engine.dispose()