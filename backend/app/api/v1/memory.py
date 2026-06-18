"""Memory API endpoints for investigation history."""
import structlog
from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models import Investigation
from app.schemas import MemoryItem, MemorySearchResponse

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.get(
    "/",
    summary="List all investigations (history)",
)
async def list_all_investigations(
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0),
    status: str | None = Query(default=None, description="Filter by status"),
    db: AsyncSession = Depends(get_db),
):
    """List all investigations for the history page."""
    from sqlalchemy import desc

    query = select(Investigation)
    if status:
        query = query.where(Investigation.status == status)

    result = await db.execute(
        query.order_by(desc(Investigation.started_at))
        .limit(limit)
        .offset(offset)
    )
    investigations = result.scalars().all()

    return {
        "investigations": [
            {
                "id": inv.id,
                "question": inv.question,
                "status": inv.status,
                "summary": inv.summary,
                "recommendations": inv.recommendations or [],
                "started_at": inv.started_at,
                "completed_at": inv.completed_at,
            }
            for inv in investigations
        ],
        "total": len(investigations),
        "limit": limit,
        "offset": offset,
    }


@router.get(
    "/investigations",
    summary="List past investigations",
)
async def list_investigations(
    limit: int = Query(default=20, le=100),
    offset: int = Query(default=0),
    db: AsyncSession = Depends(get_db),
):
    """List recent completed investigations."""
    result = await db.execute(
        select(Investigation)
        .where(Investigation.status == "completed")
        .order_by(desc(Investigation.started_at))
        .limit(limit)
        .offset(offset)
    )
    investigations = result.scalars().all()

    return {
        "investigations": [
            {
                "id": inv.id,
                "question": inv.question,
                "status": inv.status,
                "summary": inv.summary,
                "started_at": inv.started_at,
                "completed_at": inv.completed_at,
            }
            for inv in investigations
        ],
        "total": len(investigations),
    }



@router.get(
    "/investigations/{investigation_id}",
    summary="Get specific investigation",
)
async def get_investigation(
    investigation_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get details of a specific investigation."""
    result = await db.execute(
        select(Investigation).where(Investigation.id == investigation_id)
    )
    investigation = result.scalar_one_or_none()

    if not investigation:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Investigation not found",
        )

    return {
        "id": investigation.id,
        "question": investigation.question,
        "status": investigation.status,
        "intent": investigation.intent,
        "findings": investigation.findings,
        "root_causes": investigation.root_causes,
        "recommendations": investigation.recommendations,
        "summary": investigation.summary,
        "started_at": investigation.started_at,
        "completed_at": investigation.completed_at,
        "tokens_used": investigation.tokens_used,
    }


@router.get(
    "/similar",
    summary="Find similar past investigations",
    response_model=MemorySearchResponse,
)
async def find_similar(
    question: str = Query(..., description="Question to search for"),
    limit: int = Query(default=5, le=20),
    db: AsyncSession = Depends(get_db),
):
    """Find similar past investigations using keyword search."""
    # Simple keyword search — in production would use vector similarity
    keywords = [w.lower() for w in question.split() if len(w) > 3]

    query = select(Investigation).where(Investigation.status == "completed")
    result = await db.execute(
        query.order_by(desc(Investigation.started_at)).limit(100)
    )
    all_investigations = result.scalars().all()

    # Score by keyword overlap
    scored = []
    for inv in all_investigations:
        inv_words = inv.question.lower().split()
        overlap = sum(1 for kw in keywords if kw in inv_words)
        if overlap > 0:
            scored.append((inv, overlap / len(keywords)))

    # Sort by score and take top results
    scored.sort(key=lambda x: x[1], reverse=True)
    top_results = scored[:limit]

    return MemorySearchResponse(
        query=question,
        results=[
            MemoryItem(
                id=inv.id,
                question=inv.question,
                summary=inv.summary,
                started_at=inv.started_at,
                completed_at=inv.completed_at,
                similarity_score=score,
            )
            for inv, score in top_results
        ],
        total=len(top_results),
    )
