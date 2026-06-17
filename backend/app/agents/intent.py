"""Intent Agent: Parses business questions into structured investigation plans."""
from typing import Any

import structlog

from app.agents.base import BaseAgent
from app.graph.state import InvestigationState
from app.schemas import InvestigationPlan, IntentType, AnalysisType

logger = structlog.get_logger(__name__)


INTENT_AGENT_PROMPT = """You are the Intent Analyst for an AI Product Analytics Copilot.

Your role is to analyze natural language business questions and extract a structured investigation plan.

## Your Responsibilities

1. **Identify the core business question** - What metric or outcome is the user concerned about?
2. **Classify the intent type** - Is this about retention, revenue, payments, churn, features, or general analytics?
3. **Extract temporal context** - What time period is relevant? What comparison is needed?
4. **Identify relevant dimensions** - Which user segments, geographies, or features are relevant?
5. **Generate initial hypotheses** - What are the likely root causes based on the question type?
6. **Specify required analyses** - What analytical approaches are needed to answer this question?

## Intent Types

- `retention_investigation`: Questions about user retention, churn, return rates
- `revenue_investigation`: Questions about MRR, ARR, LTV, revenue trends
- `payment_failure_investigation`: Questions about failed payments, declines, fraud
- `churn_investigation`: Questions about customer/subscription cancellations
- `feature_impact_investigation`: Questions about the effect of a specific feature or change
- `engagement_investigation`: Questions about DAU, WAU, MAU, session depth, feature adoption
- `general_analytics`: General data questions that don't fit the above

## Available Analysis Types

- `cohort_retention`: Cohort-based retention analysis
- `segment_comparison`: Compare metrics across user segments
- `funnel_analysis`: Conversion funnel analysis
- `revenue_analysis`: Revenue and subscription analysis
- `churn_prediction`: Predict which users are likely to churn
- `anomaly_detection`: Detect statistical anomalies in metrics
- `root_cause`: Hypothesis testing and root cause identification

## Important Notes

- Be specific about what metrics to measure
- Always include at least 2-3 hypotheses
- Consider seasonality as a hypothesis when relevant
- Consider data quality issues as a hypothesis
- For retention questions, always include cohort_retention analysis
- For payment questions, always include revenue_analysis"""


class IntentAgent(BaseAgent):
    """Parses business questions into structured investigation plans."""

    def __init__(self):
        super().__init__("IntentAgent")

    @property
    def system_prompt(self) -> str:
        return INTENT_AGENT_PROMPT

    async def run(self, state: InvestigationState) -> dict[str, Any]:
        """Parse the question and create an investigation plan."""
        question = state["question"]
        user_context = state.get("user_context", {})

        context_str = ""
        if user_context.get("filters"):
            context_str = f"\n\nUser context filters: {user_context['filters']}"
        if user_context.get("time_range"):
            context_str += f"\nTime range: {user_context['time_range']}"

        output_schema = {
            "type": "object",
            "properties": {
                "intent_type": {
                    "type": "string",
                    "enum": [t.value for t in IntentType]
                },
                "primary_metrics": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "The main metrics relevant to this question"
                },
                "time_range": {
                    "type": "object",
                    "properties": {
                        "focus": {"type": "string"},
                        "comparison": {"type": "string"},
                        "lookback_days": {"type": "integer"}
                    }
                },
                "dimensions": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "User segments and dimensions to analyze"
                },
                "hypotheses": {
                    "type": "array",
                    "items": {"type": "string"},
                    "minItems": 2,
                    "description": "Initial hypotheses about root causes"
                },
                "required_analyses": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [a.value for a in AnalysisType]
                    }
                },
                "priority": {
                    "type": "string",
                    "enum": ["low", "medium", "high", "critical"]
                },
                "reasoning": {
                    "type": "string",
                    "description": "Brief explanation of the investigation approach"
                }
            },
            "required": ["intent_type", "primary_metrics", "hypotheses", "required_analyses", "priority"]
        }

        response = await self.structured_chat(
            messages=[{
                "role": "human",
                "content": f"Analyze this business question and create an investigation plan:\n\n{question}{context_str}"
            }],
            output_schema=output_schema,
        )

        # Build the intent plan
        intent = InvestigationPlan(
            intent_type=IntentType(response["intent_type"]),
            primary_metrics=response["primary_metrics"],
            time_range=response.get("time_range"),
            dimensions=response.get("dimensions", []),
            hypotheses=response["hypotheses"],
            required_analyses=[AnalysisType(a) for a in response.get("required_analyses", [])],
            priority=response.get("priority", "medium"),
            reasoning=response.get("reasoning"),
        )

        logger.info(
            "Intent parsed",
            intent_type=intent.intent_type,
            primary_metrics=intent.primary_metrics,
            hypothesis_count=len(intent.hypotheses),
            investigation_id=state["investigation_id"],
        )

        return {
            "intent": intent,
            "intent_reasoning": response.get("reasoning"),
        }