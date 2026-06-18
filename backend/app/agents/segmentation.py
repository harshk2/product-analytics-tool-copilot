"""Segmentation Agent: Segments users/customers by behavior patterns."""
from typing import Any

import structlog

from app.agents.base import BaseAgent
from app.graph.state import InvestigationState
from app.schemas import Segment, SegmentationResult

logger = structlog.get_logger(__name__)

SEGMENTATION_PROMPT = """You are the Segmentation Analyst for an AI Product Analytics Copilot.

Your role is to identify meaningful user segments and their behavioral patterns.

## Segmentation Frameworks

### Behavioral Segmentation
Segment users by how they use the product:
- **Power Users**: High engagement, many features, long sessions
- **Regular Users**: Moderate engagement, consistent usage
- **Casual Users**: Low frequency, limited features
- **At-Risk Users**: Declining engagement, possible churners
- **Dormant Users**: No recent activity (30+ days)

### Value-Based Segmentation
Segment by business value:
- **Champions**: Highest LTV, advocates
- **Loyal**: High retention, consistent payment
- **Promising**: Growing usage, potential upsell
- **At-Risk**: Previously active, now declining
- **Lost**: Churned or canceled

### Plan-Based Segmentation
- Enterprise, Pro, Starter, Free users behave differently
- Analyze plan-level differences to identify upgrade/downgrade drivers

## Analysis Responsibilities

1. **Identify which segments are most affected** by the metric change
2. **Calculate segment-level metrics** (retention, revenue, engagement)
3. **Find high-risk segments** that need intervention
4. **Identify high-value segments** that need protection
5. **Suggest segment-specific actions**

## Output Requirements

For each segment provide:
- Clear definition
- User count and percentage
- Key characteristics
- Risk level (low/medium/high/critical)
- Recommended action"""


class SegmentationAgent(BaseAgent):
    """Segments users/customers by behavior patterns."""

    def __init__(self):
        super().__init__("SegmentationAgent")

    @property
    def system_prompt(self) -> str:
        return SEGMENTATION_PROMPT

    async def run(self, state: InvestigationState) -> dict[str, Any]:
        """Analyze and segment users based on available data."""
        raw_data = state.get("raw_data", [])
        intent = state.get("intent")
        question = state["question"]

        if not raw_data:
            return {"warnings": ["SegmentationAgent: No data available for segmentation"]}

        analysis_prompt = f"""Analyze the user data and identify meaningful segments for this investigation:

**Question**: {question}
**Intent**: {intent.intent_type.value if intent else 'unknown'}

**Available Data**:
{self._format_data(raw_data)}

Identify user segments that:
1. Are most relevant to the metric change being investigated
2. Show differential behavior (some segments worse than others)
3. Represent actionable opportunities (can we fix something for this segment?)

Calculate segment sizes, characteristics, and risk levels."""

        response = await self.structured_chat(
            messages=[{"role": "human", "content": analysis_prompt}],
            output_schema={
                "type": "object",
                "properties": {
                    "segments": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "definition": {"type": "string"},
                                "user_count": {"type": "integer"},
                                "percentage": {"type": "number"},
                                "characteristics": {"type": "object"},
                                "risk_level": {
                                    "type": "string",
                                    "enum": ["low", "medium", "high", "critical"]
                                }
                            },
                            "required": ["name", "definition", "user_count", "percentage", "risk_level"]
                        }
                    },
                    "method": {"type": "string"},
                    "total_users": {"type": "integer"},
                    "recommendations": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "segment": {"type": "string"},
                                "action": {"type": "string"},
                                "priority": {"type": "string"}
                            }
                        }
                    }
                },
                "required": ["segments", "total_users"]
            }
        )

        segmentation_result = SegmentationResult(
            segments=[
                Segment(
                    name=s["name"],
                    definition=s["definition"],
                    user_count=s["user_count"],
                    percentage=s["percentage"],
                    characteristics=s.get("characteristics", {}),
                    risk_level=s.get("risk_level"),
                )
                for s in response.get("segments", [])
            ],
            method=response.get("method", "behavioral"),
            total_users=response.get("total_users", 0),
            recommendations=response.get("recommendations", []),
        )

        logger.info(
            "Segmentation completed",
            segment_count=len(segmentation_result.segments),
            total_users=segmentation_result.total_users,
        )

        return {"segmentation": segmentation_result}

    def _format_data(self, raw_data: list[dict]) -> str:
        """Format data for the LLM prompt."""
        formatted = []
        for d in raw_data[:3]:
            name = d.get("query_name", "Dataset")
            rows = d.get("data", [])[:20]
            formatted.append(f"**{name}** ({d.get('row_count', len(rows))} rows):\n{rows}")
        return "\n\n".join(formatted) if formatted else "No data available"
