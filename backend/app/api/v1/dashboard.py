"""Dashboard API endpoints with KPIs and alerts."""
from datetime import datetime, timedelta

import structlog
from fastapi import APIRouter, Depends
from sqlalchemy import func, select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models import Investigation
from app.schemas import DashboardResponse, KPIValue, DashboardAlert

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.get(
    "/",
    response_model=DashboardResponse,
    summary="Get dashboard data",
)
async def get_dashboard(
    db: AsyncSession = Depends(get_db),
):
    """Get KPIs, alerts, and recent investigations for the dashboard."""
    now = datetime.utcnow()
    week_ago = now - timedelta(days=7)
    prev_week = week_ago - timedelta(days=7)

    # ── Compute KPIs ──────────────────────────────────────────────────────────
    # Note: In a real deployment, these would query actual user/event tables
    # Here we show the query pattern

    try:
        # Active Users KPI
        from app.models import User, Event

        # Current week DAU (average)
        curr_dau_result = await db.execute(
            select(func.count(func.distinct(Event.user_id)))
            .where(Event.occurred_at >= week_ago)
        )
        curr_dau = (curr_dau_result.scalar() or 0) / 7  # avg per day

        prev_dau_result = await db.execute(
            select(func.count(func.distinct(Event.user_id)))
            .where(and_(Event.occurred_at >= prev_week, Event.occurred_at < week_ago))
        )
        prev_dau = (prev_dau_result.scalar() or 0) / 7

        dau_change = curr_dau - prev_dau
        dau_change_pct = (dau_change / prev_dau * 100) if prev_dau > 0 else 0

        kpis = {
            "dau": KPIValue(
                value=round(curr_dau),
                change=round(dau_change),
                change_pct=round(dau_change_pct, 1),
                trend="up" if dau_change > 0 else "down" if dau_change < 0 else "flat",
                is_good_change=dau_change >= 0,
            ),
            "investigations_this_week": KPIValue(
                value=(await db.execute(
                    select(func.count(Investigation.id))
                    .where(Investigation.started_at >= week_ago)
                )).scalar() or 0,
                change=0,
                change_pct=0,
                trend="flat",
                is_good_change=True,
            ),
        }

    except Exception as e:
        logger.warning("Could not compute all KPIs", error=str(e))
        # Return minimal KPIs if tables don't exist yet
        kpis = {
            "status": KPIValue(
                value=1,
                change=0,
                change_pct=0,
                trend="flat",
                is_good_change=True,
            )
        }

    # ── Recent Investigations ─────────────────────────────────────────────────
    from sqlalchemy import desc

    recent_result = await db.execute(
        select(Investigation)
        .order_by(desc(Investigation.started_at))
        .limit(5)
    )
    recent_investigations = recent_result.scalars().all()

    return DashboardResponse(
        kpis=kpis,
        alerts=[],
        recent_investigations=[
            {
                "id": inv.id,
                "question": inv.question,
                "status": inv.status,
                "summary": inv.summary,
                "started_at": inv.started_at,
            }
            for inv in recent_investigations
        ],
        updated_at=now,
    )


@router.get(
    "/kpis",
    summary="Get KPI metrics",
)
async def get_kpis(db: AsyncSession = Depends(get_db)):
    """Get key performance indicators."""
    dashboard = await get_dashboard(db)
    return {"kpis": dashboard.kpis}


@router.get(
    "/alerts",
    summary="Get active alerts",
)
async def get_alerts(db: AsyncSession = Depends(get_db)):
    """Get currently active metric alerts."""
    # In production: check metrics against thresholds
    return {"alerts": []}