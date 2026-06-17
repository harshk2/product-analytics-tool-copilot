"""Investigation-related Celery tasks."""
import asyncio
import uuid
from datetime import datetime, timedelta

import structlog
from celery import Task

from app.tasks.celery_app import celery_app

logger = structlog.get_logger(__name__)


class AsyncTask(Task):
    """Base task that runs async functions synchronously."""

    def run_async(self, coro):
        """Run an async coroutine in a new event loop."""
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()


@celery_app.task(
    bind=True,
    base=AsyncTask,
    name="app.tasks.investigations.run_investigation_async",
    queue="investigations",
    max_retries=2,
    soft_time_limit=300,
)
def run_investigation_async(self, investigation_id: str, question: str, session_id: str | None = None):
    """Run an investigation asynchronously via Celery.

    This is used for long-running investigations that shouldn't block HTTP requests.
    Results are stored in the investigations table.

    Args:
        investigation_id: UUID of the pre-created investigation record.
        question: The business question to investigate.
        session_id: Optional session ID for context.
    """
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
    from sqlalchemy.orm import sessionmaker
    from app.config import settings
    from app.graph.compiler import InvestigationGraph
    from app.models import Investigation
    from sqlalchemy import select

    async def _run():
        engine = create_async_engine(settings.DATABASE_URL, echo=False)
        AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with AsyncSessionLocal() as db:
            try:
                graph = InvestigationGraph(db)
                final_state = await graph.run(
                    investigation_id=investigation_id,
                    question=question,
                    session_id=session_id,
                )

                # Save results to DB
                result = await db.execute(
                    select(Investigation).where(Investigation.id == investigation_id)
                )
                investigation = result.scalar_one_or_none()

                if investigation and final_state.get("executive_summary"):
                    es = final_state["executive_summary"]
                    investigation.summary = es.summary
                    investigation.findings = [f for f in es.key_findings]
                    investigation.recommendations = [
                        {
                            "action": r.action,
                            "impact": r.impact,
                            "effort": r.effort,
                            "urgency": r.urgency,
                            "expected_outcome": r.expected_outcome,
                        }
                        for r in es.recommendations
                    ]
                    investigation.status = "completed"
                    investigation.completed_at = datetime.utcnow()
                    await db.commit()

                logger.info(
                    "Async investigation completed",
                    investigation_id=investigation_id,
                )
                return {"status": "completed", "investigation_id": investigation_id}

            except Exception as e:
                logger.error(
                    "Async investigation failed",
                    investigation_id=investigation_id,
                    error=str(e),
                    exc_info=True,
                )
                raise self.retry(exc=e, countdown=60)
            finally:
                await engine.dispose()

    return self.run_async(_run())


@celery_app.task(
    name="app.tasks.investigations.cleanup_stale_investigations",
    queue="default",
)
def cleanup_stale_investigations():
    """Mark investigations that have been in_progress for more than 1 hour as failed.

    This prevents orphaned investigations from stale SSE streams.
    """
    from sqlalchemy import create_engine, update
    from sqlalchemy.orm import sessionmaker
    from app.config import settings
    from app.models import Investigation

    engine = create_engine(settings.DATABASE_URL_SYNC)
    Session = sessionmaker(engine)
    stale_threshold = datetime.utcnow() - timedelta(hours=1)

    with Session() as session:
        result = session.execute(
            update(Investigation)
            .where(
                Investigation.status == "in_progress",
                Investigation.started_at < stale_threshold,
            )
            .values(
                status="failed",
                completed_at=datetime.utcnow(),
            )
            .returning(Investigation.id)
        )
        stale_count = len(result.fetchall())
        session.commit()

    logger.info("Cleaned up stale investigations", count=stale_count)
    return {"cleaned_up": stale_count}
