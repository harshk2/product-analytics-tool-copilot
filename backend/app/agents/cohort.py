"""Cohort Analysis Agent: Performs cohort-based retention and revenue analysis."""
from typing import Any

import structlog

from app.agents.base import BaseAgent
from app.graph.state import InvestigationState
from app.schemas import CohortAnalysisResult, CohortData

logger = structlog.get_logger(__name__)

COHORT_AGENT_PROMPT = """You are the Cohort Analysis specialist for an AI Product Analytics Copilot.

Your role is to analyze cohort data and identify retention and revenue trends.

## Cohort Analysis Framework

A cohort is a group of users who share a common starting point (e.g., signup week/month).

### Retention Cohort Analysis
- Track what percentage of users from cohort N return in period N+1, N+2, etc.
- Identify if newer cohorts retain better/worse than older ones
- Find the "retention knee" — where drop-off accelerates

### Revenue Cohort Analysis
- Track revenue from cohorts over time
- Calculate LTV curves
- Identify high-value vs low-value cohorts

## Analysis Responsibilities

1. **Calculate retention rates** from raw event data
2. **Identify cohort trends** (improving, declining, stable)
3. **Find anomalies** in specific cohort periods
4. **Calculate statistical significance** of changes
5. **Generate insights** from the cohort patterns

## Output Format

Always provide:
- Retention rates by period (Week 0, Week 1, Week 2, ...)
- Trend direction for each cohort
- Statistical significance of changes
- Comparison to baseline/benchmark
- Specific insights about what the data shows"""


class CohortAnalysisAgent(BaseAgent):
    """Performs cohort-based retention and revenue analysis."""

    def __init__(self):
        super().__init__("CohortAnalysisAgent")

    @property
    def system_prompt(self) -> str:
        return COHORT_AGENT_PROMPT

    async def run(self, state: InvestigationState) -> dict[str, Any]:
        """Analyze cohort data from raw query results."""
        raw_data = state.get("raw_data", [])
        intent = state.get("intent")

        if not raw_data:
            return {"warnings": ["CohortAnalysisAgent: No data available for cohort analysis"]}

        # Find retention-related query results
        cohort_data = [d for d in raw_data if
                       "retention" in (d.get("query_name") or "").lower() or
                       "cohort" in (d.get("query_name") or "").lower()]

        if not cohort_data:
            # Use whatever data we have
            cohort_data = raw_data

        # Ask LLM to analyze the cohort data and extract patterns
        analysis_prompt = f"""Analyze this cohort data for the investigation:

**Question**: {state['question']}
**Intent**: {intent.intent_type.value if intent else 'unknown'}

**Available Data**:
{self._format_data_for_analysis(cohort_data)}

Analyze the cohort retention patterns and provide:
1. Retention rates by week/period
2. Cohort sizes
3. Notable trends (improving, declining, anomalies)
4. Specific insights about changes over time
5. Statistical significance of any changes

If the raw data doesn't contain pre-computed cohort data, compute it from the available event data."""

        response = await self.structured_chat(
            messages=[{"role": "human", "content": analysis_prompt}],
            output_schema={
                "type": "object",
                "properties": {
                    "cohort_type": {"type": "string"},
                    "cohorts": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "period": {"type": "string"},
                                "size": {"type": "integer"},
                                "retention": {
                                    "type": "array",
                                    "items": {"type": "number"}
                                }
                            },
                            "required": ["period", "size", "retention"]
                        }
                    },
                    "average_retention": {
                        "type": "array",
                        "items": {"type": "number"}
                    },
                    "insights": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "metric": {"type": "string"},
                                "value": {},
                                "trend": {"type": "string"},
                                "change": {"type": "number"},
                                "significance": {"type": "string"},
                                "description": {"type": "string"}
                            }
                        }
                    }
                },
                "required": ["cohort_type", "cohorts", "insights"]
            }
        )

        cohort_result = CohortAnalysisResult(
            cohort_type=response.get("cohort_type", "weekly_retention"),
            cohorts=[
                CohortData(
                    period=c["period"],
                    size=c["size"],
                    retention=c["retention"],
                )
                for c in response.get("cohorts", [])
            ],
            average_retention=response.get("average_retention", []),
            insights=response.get("insights", []),
        )

        logger.info(
            "Cohort analysis completed",
            cohort_count=len(cohort_result.cohorts),
            insight_count=len(cohort_result.insights),
        )

        return {"cohort_analysis": cohort_result}

    def _format_data_for_analysis(self, data: list[dict[str, Any]]) -> str:
        """Format raw data for LLM analysis."""
        formatted = []
        for dataset in data:
            name = dataset.get("query_name", "Dataset")
            rows = dataset.get("data", [])[:50]  # Limit for context
            formatted.append(f"\n### {name}\n```json\n{rows}\n```")
        return "\n".join(formatted) if formatted else "No data available"
