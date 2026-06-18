"""LangGraph workflow compilation and execution."""
from collections.abc import AsyncGenerator
from typing import Any

import structlog
from langgraph.graph import END, StateGraph
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.cohort import CohortAnalysisAgent
from app.agents.intent import IntentAgent
from app.agents.metrics import MetricsAgent
from app.agents.root_cause import RootCauseAgent
from app.agents.segmentation import SegmentationAgent
from app.agents.sql import SQLAgent
from app.agents.summary import ExecutiveSummaryAgent
from app.agents.visualization import VisualizationAgent
from app.graph.state import InvestigationState, create_initial_state
from app.schemas import AnalysisType, InvestigationStatus

logger = structlog.get_logger(__name__)


def should_run_cohort_analysis(state: InvestigationState) -> str:
    """Route to cohort analysis if required."""
    intent = state.get("intent")
    if not intent:
        return "skip_analysis"

    required = [a.value for a in intent.required_analyses]
    if AnalysisType.COHORT_RETENTION.value in required:
        return "cohort_analysis"
    return "segmentation"


def should_run_segmentation(state: InvestigationState) -> str:
    """Route to segmentation if required."""
    intent = state.get("intent")
    if not intent:
        return "root_cause"

    required = [a.value for a in intent.required_analyses]
    if AnalysisType.SEGMENT_COMPARISON.value in required:
        return "segmentation"
    return "root_cause"


def check_for_errors(state: InvestigationState) -> str:
    """Check if there are critical errors that should halt the workflow."""
    errors = state.get("errors", [])
    if len(errors) > 5:  # Too many errors, something is fundamentally wrong
        return "error"
    return "continue"


class InvestigationGraph:
    """Compiles and executes the investigation workflow."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self._graph = self._build_graph()

    def _build_graph(self) -> Any:
        """Build the LangGraph workflow."""
        # Initialize agents
        intent_agent = IntentAgent()
        metrics_agent = MetricsAgent()
        sql_agent = SQLAgent(self.db)
        cohort_agent = CohortAnalysisAgent()
        seg_agent = SegmentationAgent()
        root_cause_agent = RootCauseAgent()
        viz_agent = VisualizationAgent()
        summary_agent = ExecutiveSummaryAgent()

        # Create the state graph
        workflow = StateGraph(InvestigationState)

        # ── Add nodes ──────────────────────────────────────────────────────────
        workflow.add_node("intent", intent_agent.invoke)
        workflow.add_node("metrics", metrics_agent.invoke)
        workflow.add_node("sql_generation", sql_agent.invoke)
        workflow.add_node("cohort_analysis", cohort_agent.invoke)
        workflow.add_node("segmentation", seg_agent.invoke)
        workflow.add_node("root_cause", root_cause_agent.invoke)
        workflow.add_node("visualization", viz_agent.invoke)
        workflow.add_node("summary", summary_agent.invoke)

        # ── Add edges ──────────────────────────────────────────────────────────
        # Entry point
        workflow.set_entry_point("intent")

        # Intent → Metrics → SQL (always)
        workflow.add_edge("intent", "metrics")
        workflow.add_edge("metrics", "sql_generation")

        # SQL → Analysis (conditional based on intent)
        workflow.add_conditional_edges(
            "sql_generation",
            should_run_cohort_analysis,
            {
                "cohort_analysis": "cohort_analysis",
                "segmentation": "segmentation",
                "skip_analysis": "root_cause",
            }
        )

        # Cohort → Segmentation (conditional)
        workflow.add_conditional_edges(
            "cohort_analysis",
            should_run_segmentation,
            {
                "segmentation": "segmentation",
                "root_cause": "root_cause",
            }
        )

        # Segmentation → Root Cause (always)
        workflow.add_edge("segmentation", "root_cause")

        # Root Cause → Visualization (always)
        workflow.add_edge("root_cause", "visualization")

        # Visualization → Summary (always)
        workflow.add_edge("visualization", "summary")

        # Summary → End
        workflow.add_edge("summary", END)

        return workflow.compile()

    async def run(self, investigation_id: str, question: str, **kwargs) -> InvestigationState:
        """Run the full investigation workflow.

        Args:
            investigation_id: Unique ID for this investigation.
            question: The business question to investigate.
            **kwargs: Additional state fields (session_id, user_context).

        Returns:
            Final investigation state.
        """
        initial_state = create_initial_state(
            investigation_id=investigation_id,
            question=question,
            session_id=kwargs.get("session_id"),
            user_context=kwargs.get("user_context", {}),
        )

        logger.info(
            "Investigation started",
            investigation_id=investigation_id,
            question=question[:100],
        )

        try:
            final_state = await self._graph.ainvoke(initial_state)
            final_state["status"] = InvestigationStatus.COMPLETED
            logger.info(
                "Investigation completed",
                investigation_id=investigation_id,
            )
            return final_state

        except Exception as e:
            logger.error(
                "Investigation failed",
                investigation_id=investigation_id,
                error=str(e),
                exc_info=True,
            )
            initial_state["status"] = InvestigationStatus.FAILED
            initial_state["errors"].append(f"Fatal error: {str(e)}")
            return initial_state

    async def stream(
        self,
        investigation_id: str,
        question: str,
        **kwargs
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Stream investigation progress as Server-Sent Events.

        Yields event dicts with type, agent, data, and message fields.
        """
        initial_state = create_initial_state(
            investigation_id=investigation_id,
            question=question,
            session_id=kwargs.get("session_id"),
            user_context=kwargs.get("user_context", {}),
        )

        yield {
            "type": "investigation_start",
            "data": {"investigation_id": investigation_id},
            "message": "Starting investigation...",
        }

        try:
            agent_name_map = {
                "intent": "Intent Analyst",
                "metrics": "Metrics Analyst",
                "sql_generation": "SQL Agent",
                "cohort_analysis": "Cohort Analyst",
                "segmentation": "Segmentation Analyst",
                "root_cause": "Root Cause Analyst",
                "visualization": "Visualization Designer",
                "summary": "Executive Summary Writer",
            }

            async for event in self._graph.astream(initial_state):
                # LangGraph streams partial state updates
                for node_name, state_update in event.items():
                    if node_name == "__end__":
                        continue

                    agent_display = agent_name_map.get(node_name, node_name)

                    # Emit thinking event
                    yield {
                        "type": "thinking",
                        "agent": node_name,
                        "message": f"{agent_display} is analyzing...",
                        "data": {},
                    }

                    # Emit findings based on what was updated
                    if state_update.get("intent"):
                        intent = state_update["intent"]
                        yield {
                            "type": "finding",
                            "agent": node_name,
                            "data": {
                                "type": "intent",
                                "intent_type": intent.intent_type.value,
                                "metrics": intent.primary_metrics,
                                "hypotheses": intent.hypotheses[:3],
                            },
                            "message": f"Identified {len(intent.hypotheses)} hypotheses to investigate",
                        }

                    if state_update.get("metric_values"):
                        mvs = state_update["metric_values"]
                        significant = [m for m in mvs if m.is_significant]
                        yield {
                            "type": "finding",
                            "agent": node_name,
                            "data": {
                                "type": "metrics",
                                "metrics": [
                                    {
                                        "name": m.metric,
                                        "value": m.value,
                                        "change_pct": m.change_pct,
                                        "is_significant": m.is_significant,
                                    }
                                    for m in mvs
                                ],
                            },
                            "message": f"Identified {len(significant)} significant metric changes",
                        }

                    if state_update.get("raw_data"):
                        data_count = len(state_update["raw_data"])
                        yield {
                            "type": "finding",
                            "agent": node_name,
                            "data": {"type": "data", "query_count": data_count},
                            "message": f"Executed {data_count} queries",
                        }

                    if state_update.get("cohort_analysis"):
                        ca = state_update["cohort_analysis"]
                        yield {
                            "type": "finding",
                            "agent": node_name,
                            "data": {
                                "type": "cohort_analysis",
                                "cohort_count": len(ca.cohorts),
                                "insights": ca.insights[:3],
                            },
                            "message": f"Analyzed {len(ca.cohorts)} cohorts",
                        }

                    if state_update.get("root_cause"):
                        rc = state_update["root_cause"]
                        yield {
                            "type": "finding",
                            "agent": node_name,
                            "data": {
                                "type": "root_cause",
                                "summary": rc.summary,
                                "confidence": rc.confidence,
                                "hypothesis_count": len(rc.hypotheses),
                            },
                            "message": f"Root cause identified with {rc.confidence:.0%} confidence",
                        }

                    if state_update.get("executive_summary"):
                        es = state_update["executive_summary"]
                        yield {
                            "type": "finding",
                            "agent": node_name,
                            "data": {
                                "type": "executive_summary",
                                "summary": es.summary,
                                "recommendation_count": len(es.recommendations),
                            },
                            "message": "Executive summary ready",
                        }

                    if state_update.get("visualizations"):
                        vizs = state_update["visualizations"]
                        yield {
                            "type": "finding",
                            "agent": node_name,
                            "data": {
                                "type": "visualizations",
                                "count": len(vizs),
                                "charts": [{"id": v.id, "type": v.type, "title": v.title} for v in vizs],
                            },
                            "message": f"Created {len(vizs)} visualization(s)",
                        }

            yield {
                "type": "complete",
                "data": {"investigation_id": investigation_id},
                "message": "Investigation complete",
            }

        except Exception as e:
            logger.error(
                "Stream investigation failed",
                investigation_id=investigation_id,
                error=str(e),
                exc_info=True,
            )
            yield {
                "type": "error",
                "data": {"error": str(e)},
                "message": f"Investigation failed: {str(e)}",
            }
