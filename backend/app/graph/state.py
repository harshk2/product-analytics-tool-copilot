"""LangGraph state definition for the investigation workflow."""
from datetime import datetime
from typing import Annotated, Any

from typing_extensions import TypedDict

from app.schemas import (
    CohortAnalysisResult,
    ExecutiveSummary,
    InvestigationPlan,
    InvestigationStatus,
    MetricValue,
    RootCauseResult,
    SegmentationResult,
    SQLGenerationResult,
    Visualization,
)


def merge_list(a: list, b: list) -> list:
    """Merge two lists for annotated state fields."""
    return a + b


def take_last(a: Any, b: Any) -> Any:
    """Take the last value for non-list state fields."""
    return b if b is not None else a


class InvestigationState(TypedDict):
    """Shared state passed through all agents in the investigation graph.

    Each field uses an annotation to specify how it should be merged
    when multiple agents update the same field.
    """

    # ─── Input ────────────────────────────────────────────────────────────────
    investigation_id: str
    question: str
    session_id: str | None
    user_context: dict[str, Any]

    # ─── Phase 1: Intent ──────────────────────────────────────────────────────
    intent: InvestigationPlan | None
    intent_reasoning: str | None

    # ─── Phase 2: Metrics ─────────────────────────────────────────────────────
    metric_definitions: list[dict[str, Any]]
    metric_values: Annotated[list[MetricValue], merge_list]
    data_sources: list[dict[str, Any]]
    investigation_focus: str | None  # The single most important metric to focus on

    # ─── Phase 3: SQL & Data ──────────────────────────────────────────────────
    generated_queries: Annotated[list[SQLGenerationResult], merge_list]
    raw_data: Annotated[list[dict[str, Any]], merge_list]  # Results from SQL queries

    # ─── Phase 4: Analysis ────────────────────────────────────────────────────
    cohort_analysis: CohortAnalysisResult | None
    segmentation: SegmentationResult | None
    anomalies: Annotated[list[dict[str, Any]], merge_list]

    # ─── Phase 5: Root Cause ──────────────────────────────────────────────────
    root_cause: RootCauseResult | None

    # ─── Phase 6: Visualization ───────────────────────────────────────────────
    visualizations: Annotated[list[Visualization], merge_list]

    # ─── Phase 7: Summary ─────────────────────────────────────────────────────
    executive_summary: ExecutiveSummary | None

    # ─── Metadata ─────────────────────────────────────────────────────────────
    status: InvestigationStatus
    errors: Annotated[list[str], merge_list]
    warnings: Annotated[list[str], merge_list]
    agent_trace: Annotated[list[dict[str, Any]], merge_list]  # Audit trail

    # Token tracking
    total_tokens: int
    total_cost_cents: int

    # Timestamps
    started_at: datetime
    completed_at: datetime | None


def create_initial_state(
    investigation_id: str,
    question: str,
    session_id: str | None = None,
    user_context: dict[str, Any] | None = None,
) -> InvestigationState:
    """Create the initial state for an investigation."""
    return InvestigationState(
        # Input
        investigation_id=investigation_id,
        question=question,
        session_id=session_id,
        user_context=user_context or {},

        # Intent
        intent=None,
        intent_reasoning=None,

        # Metrics
        metric_definitions=[],
        metric_values=[],
        data_sources=[],
        investigation_focus=None,

        # SQL & Data
        generated_queries=[],
        raw_data=[],

        # Analysis
        cohort_analysis=None,
        segmentation=None,
        anomalies=[],

        # Root Cause
        root_cause=None,

        # Visualization
        visualizations=[],

        # Summary
        executive_summary=None,

        # Metadata
        status=InvestigationStatus.IN_PROGRESS,
        errors=[],
        warnings=[],
        agent_trace=[],

        # Token tracking
        total_tokens=0,
        total_cost_cents=0,

        # Timestamps
        started_at=datetime.utcnow(),
        completed_at=None,
    )
