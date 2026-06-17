"""Metrics Agent: Identifies and quantifies relevant metrics for an investigation."""
from typing import Any
from datetime import datetime, timedelta

import structlog

from app.agents.base import BaseAgent
from app.graph.state import InvestigationState
from app.schemas import MetricValue

logger = structlog.get_logger(__name__)

METRICS_AGENT_PROMPT = """You are the Metrics Analyst for an AI Product Analytics Copilot.

Your role is to translate an investigation plan into specific, measurable metric definitions
that can be retrieved from the database and compared.

## Your Responsibilities

1. **Map intent → concrete metrics**: Convert abstract business questions into measurable KPIs
2. **Define measurement windows**: Specify exact time periods for current vs. comparison
3. **Identify data sources**: Which tables and columns to query for each metric
4. **Estimate baseline values**: What's the typical/expected value for each metric?
5. **Calculate metric changes**: Quantify the change (absolute + percentage)

## Available Metrics by Category

### Retention Metrics
- `weekly_retention_rate`: % users active in week N who return in week N+1
- `monthly_retention_rate`: % users active in month M who return in month M+1
- `day1_retention`, `day7_retention`, `day30_retention`: Nth day retention
- `churn_rate`: % active users who become inactive in a period

### Revenue Metrics
- `mrr`: Monthly Recurring Revenue (sum of active subscription amounts)
- `arr`: Annual Recurring Revenue (MRR × 12)
- `new_mrr`: MRR from new subscriptions in period
- `expansion_mrr`: MRR increase from plan upgrades
- `churned_mrr`: MRR lost from cancellations
- `average_revenue_per_user`: MRR / total active users

### Engagement Metrics
- `dau`: Daily Active Users
- `wau`: Weekly Active Users
- `mau`: Monthly Active Users
- `dau_mau_ratio`: Engagement stickiness (DAU/MAU)
- `avg_session_duration`: Average time per session
- `feature_adoption_rate`: % users who used a feature

### Payment Metrics
- `payment_success_rate`: % of payment attempts that succeed
- `payment_failure_rate`: % of payment attempts that fail
- `avg_payment_amount`: Average transaction value
- `chargeback_rate`: % of payments resulting in chargebacks
- `risk_flagged_rate`: % of payments flagged as high-risk

### Conversion Metrics
- `signup_to_paid_rate`: % users who convert from free to paid
- `trial_conversion_rate`: % trial users who convert to paid
- `funnel_completion_rate`: % users completing key funnels

## Output Requirements

For each identified metric:
- Specify the exact measurement window (e.g., "2024-W01 vs 2024-W02")
- Include both absolute value and period-over-period change
- Flag if the change is statistically significant (> 10% change)
- Note any caveats (e.g., low sample size, seasonal effects)"""


class MetricsAgent(BaseAgent):
    """Identifies and quantifies relevant metrics for an investigation."""

    def __init__(self):
        super().__init__("MetricsAgent")

    @property
    def system_prompt(self) -> str:
        return METRICS_AGENT_PROMPT

    async def run(self, state: InvestigationState) -> dict[str, Any]:
        """Identify relevant metrics and estimate their current vs. baseline values."""
        intent = state.get("intent")
        if not intent:
            return {"errors": ["MetricsAgent: No intent provided"]}

        question = state["question"]
        now = datetime.utcnow()

        # Determine time windows from intent
        time_range = intent.time_range or {}
        lookback_days = time_range.get("lookback_days", 30)
        focus_period = time_range.get("focus", "last_week")
        comparison_period = time_range.get("comparison", "previous_week")

        # Build prompt for metric identification
        prompt = self._build_metrics_prompt(
            question=question,
            intent_type=intent.intent_type.value,
            primary_metrics=intent.primary_metrics,
            dimensions=intent.dimensions,
            focus_period=focus_period,
            comparison_period=comparison_period,
            lookback_days=lookback_days,
            now=now,
        )

        response = await self.structured_chat(
            messages=[{"role": "human", "content": prompt}],
            output_schema={
                "type": "object",
                "properties": {
                    "metrics": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "display_name": {"type": "string"},
                                "description": {"type": "string"},
                                "current_value": {"type": "number"},
                                "previous_value": {"type": "number"},
                                "change": {"type": "number"},
                                "change_pct": {"type": "number"},
                                "period": {"type": "string"},
                                "is_significant": {"type": "boolean"},
                                "unit": {"type": "string"},
                                "table": {"type": "string"},
                                "notes": {"type": "string"}
                            },
                            "required": ["name", "display_name", "current_value", "period"]
                        },
                        "minItems": 1
                    },
                    "investigation_focus": {
                        "type": "string",
                        "description": "The single most important metric to focus on"
                    },
                    "data_availability": {
                        "type": "string",
                        "description": "Assessment of data availability for this investigation"
                    }
                },
                "required": ["metrics", "investigation_focus"]
            }
        )

        # Build MetricValue objects
        metric_values = []
        for m in response.get("metrics", []):
            metric_values.append(MetricValue(
                metric=m["name"],
                value=m.get("current_value", 0),
                period=m.get("period", focus_period),
                change=m.get("change"),
                change_pct=m.get("change_pct"),
                is_significant=m.get("is_significant", False),
            ))

        logger.info(
            "Metrics identified",
            metric_count=len(metric_values),
            significant_count=sum(1 for m in metric_values if m.is_significant),
            investigation_id=state["investigation_id"],
        )

        return {
            "metric_values": metric_values,
            "investigation_focus": response.get("investigation_focus", ""),
        }

    def _build_metrics_prompt(
        self,
        question: str,
        intent_type: str,
        primary_metrics: list[str],
        dimensions: list[str],
        focus_period: str,
        comparison_period: str,
        lookback_days: int,
        now: datetime,
    ) -> str:
        """Build the prompt for metric identification."""
        focus_start = now - timedelta(days=lookback_days)
        comparison_start = focus_start - timedelta(days=lookback_days)

        return f"""Identify the key metrics for this business investigation:

**Question**: {question}

**Intent Type**: {intent_type}
**Primary Metrics to Focus On**: {', '.join(primary_metrics)}
**Dimensions to Analyze**: {', '.join(dimensions) if dimensions else 'All users (no specific segmentation)'}

**Time Windows**:
- Focus Period ({focus_period}): {focus_start.strftime('%Y-%m-%d')} to {now.strftime('%Y-%m-%d')}
- Comparison Period ({comparison_period}): {comparison_start.strftime('%Y-%m-%d')} to {focus_start.strftime('%Y-%m-%d')}

For each relevant metric:
1. Provide a realistic estimated current value (use typical SaaS benchmarks as guidance)
2. Provide the estimated previous period value for comparison
3. Calculate the change and change percentage
4. Flag if the change is significant (> 10% absolute change or clearly abnormal)

Focus on 3-6 most relevant metrics. Don't include metrics that aren't clearly relevant to this question.
Use your knowledge of typical SaaS product metrics to provide reasonable estimates."""
