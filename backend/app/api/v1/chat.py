"""Chat API endpoints with SSE streaming."""
import json
import uuid
from collections.abc import AsyncGenerator
from datetime import datetime

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.graph.compiler import InvestigationGraph
from app.models import Investigation
from app.schemas import ChatRequest, InvestigationStatus

logger = structlog.get_logger(__name__)
router = APIRouter()


async def event_stream(
    events: AsyncGenerator[dict, None],
) -> AsyncGenerator[str, None]:
    """Format events as Server-Sent Events."""
    try:
        async for event in events:
            data = json.dumps(event, default=str)
            yield f"data: {data}\n\n"
    except GeneratorExit:
        logger.info("SSE client disconnected")
    except Exception as e:
        logger.error("SSE stream error", error=str(e))
        error_event = json.dumps({"type": "error", "message": str(e)})
        yield f"data: {error_event}\n\n"


@router.post(
    "/",
    summary="Start an investigation",
    description="Ask a business question and receive a streaming investigation response",
)
async def chat(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
):
    """Handle a business question and stream back investigation results."""
    investigation_id = str(uuid.uuid4())

    # Store investigation record
    investigation = Investigation(
        id=investigation_id,
        question=request.message,
        session_id=request.session_id,
        status=InvestigationStatus.IN_PROGRESS.value,
        started_at=datetime.utcnow(),
    )
    db.add(investigation)
    await db.flush()

    # Build the investigation graph
    graph = InvestigationGraph(db)

    async def generate():
        """Generate SSE events from the investigation."""
        try:
            async for event in graph.stream(
                investigation_id=investigation_id,
                question=request.message,
                session_id=request.session_id,
                user_context=request.context.model_dump() if request.context else {},
            ):
                yield event

            # Update investigation as completed
            investigation.status = InvestigationStatus.COMPLETED.value
            investigation.completed_at = datetime.utcnow()
            await db.flush()

        except Exception as e:
            logger.error("Investigation stream failed", investigation_id=investigation_id, error=str(e))
            investigation.status = InvestigationStatus.FAILED.value
            await db.flush()
            yield {"type": "error", "message": str(e)}

    return StreamingResponse(
        event_stream(generate()),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Investigation-ID": investigation_id,
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )


@router.get(
    "/{investigation_id}",
    summary="Get investigation result",
    description="Get the full result of a completed investigation",
)
async def get_investigation(
    investigation_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get a completed investigation by ID."""
    from sqlalchemy import select
    result = await db.execute(
        select(Investigation).where(Investigation.id == investigation_id)
    )
    investigation = result.scalar_one_or_none()

    if not investigation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Investigation {investigation_id} not found",
        )

    return {
        "id": investigation.id,
        "question": investigation.question,
        "status": investigation.status,
        "started_at": investigation.started_at,
        "completed_at": investigation.completed_at,
        "summary": investigation.summary,
        "findings": investigation.findings,
        "root_causes": investigation.root_causes,
        "recommendations": investigation.recommendations,
    }
