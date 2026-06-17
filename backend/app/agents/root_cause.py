"""Root Cause Analysis Agent: Generates and tests hypotheses for metric changes."""
from typing import Any

import structlog

from app.agents.base import BaseAgent
from app.graph.state import InvestigationState
from app.schemas import RootCauseResult, Hypothesis, Evidence

logger = structlog.get_logger(__name__)

ROOT_CAUSE_PROMPT = """You are the Root Cause Analyst for an AI Product Analytics Copilot.

Your role is to analyze data patterns, generate hypotheses, test them against available evidence,
and identify the most likely root cause of metric changes.

## Root Cause Analysis Framework

### Step 1: Enumerate Hypotheses
For any metric change, consider these hypothesis categories:

**Internal Changes**:
- Feature releases or changes (new checkout flow, UI changes)
- Pricing changes
- Onboarding flow changes
- Bug introductions
- Performance degradation (load times, error rates)

**External Factors**:
- Seasonality (holiday effects, end-of-month)
- Competitor actions
- Market trends
- Economic conditions

**Data Issues**:
- Tracking code changes
- Attribution model changes
- Data pipeline delays
- Dashboard miscalculations

**Segment-Specific**:
- Single segment driving aggregate change
- Geographic concentration
- New user cohort effects
- High-value user churn

### Step 2: Score Each Hypothesis

Score each hypothesis on:
- **Prior probability** (0-1): How likely is this type of cause?
- **Evidence strength** (0-1): How much does the data support it?
- **Timing correlation** (0-1): Does the timing match?
- **Magnitude match** (0-1): Does the data explain the full change?

**Confidence = mean(prior, evidence_strength, timing, magnitude)**

### Step 3: Rule Out Hypotheses

For each hypothesis, identify:
- What evidence would prove/disprove it
- What evidence you have
- Whether it can be ruled out

### Step 4: Rank and Report

Rank hypotheses by confidence. The top hypothesis with confidence > 0.7 is the root cause.
Multiple hypotheses may all be true (contributing factors).

## Output Requirements

Always provide:
- At least 2 hypotheses (even if some are ruled out)
- Evidence for and against each
- Confidence scores with reasoning
- Specific next steps to confirm/investigate further
- A clear root cause statement"""


class RootCauseAgent(BaseAgent):
    """Generates and tests hypotheses for metric changes."""

    def __init__(self):
        super().__init__("RootCauseAgent")

    @property
    def system_prompt(self) -> str:
        return ROOT_CAUSE_PROMPT

    async def run(self, state: InvestigationState) -> dict[str, Any]:
        """Analyze all available evidence and identify root causes."""
        question = state["question"]
        intent = state.get("intent")
        raw_data = state.get("raw_data", [])
        cohort_analysis = state.get("cohort_analysis")
        segmentation = state.get("segmentation")
        metric_values = state.get("metric_values", [])
        anomalies = state.get("anomalies", [])

        # Build comprehensive context for root cause analysis
        context = self._build_analysis_context(
            question=question,
            intent=intent,
            raw_data=raw_data,
            cohort_analysis=cohort_analysis,
            segmentation=segmentation,
            metric_values=metric_values,
            anomalies=anomalies,
        )

        response = await self.structured_chat(
            messages=[{"role": "human", "content": context}],
            output_schema={
                "type": "object",
                "properties": {
                    "hypotheses": {
                        "type": "array",
                        "minItems": 1,
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "string"},
                                "description": {"type": "string"},
                                "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                                "prior_probability": {"type": "number"},
                                "evidence": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "type": {"type": "string"},
                                            "description": {"type": "string"},
                                            "metric": {"type": "string"},
                                            "value": {},
                                            "confidence": {"type": "number"}
                                        },
                                        "required": ["type", "description", "confidence"]
                                    }
                                },
                                "ruled_out": {"type": "boolean"},
                                "ruled_out_reason": {"type": "string"},
                                "next_steps": {
                                    "type": "array",
                                    "items": {"type": "string"}
                                },
                                "category": {"type": "string"}
                            },
                            "required": ["id", "description", "confidence", "evidence", "ruled_out", "next_steps"]
                        }
                    },
                    "root_cause_id": {
                        "type": "string",
                        "description": "ID of the most likely root cause hypothesis"
                    },
                    "overall_confidence": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 1
                    },
                    "summary": {
                        "type": "string",
                        "description": "Plain English summary of the root cause"
                    }
                },
                "required": ["hypotheses", "overall_confidence", "summary"]
            }
        )

        # Build typed result
        hypotheses = []
        for h in response.get("hypotheses", []):
            evidence_list = []
            for e in h.get("evidence", []):
                evidence_list.append(Evidence(
                    type=e.get("type", "correlation"),
                    description=e["description"],
                    metric=e.get("metric"),
                    value=e.get("value"),
                    confidence=e.get("confidence", 0.5),
                ))

            hypotheses.append(Hypothesis(
                id=h["id"],
                description=h["description"],
                confidence=h["confidence"],
                evidence=evidence_list,
                ruled_out=h.get("ruled_out", False),
                next_steps=h.get("next_steps", []),
            ))

        root_cause_result = RootCauseResult(
            hypotheses=hypotheses,
            root_cause=response.get("root_cause_id"),
            confidence=response.get("overall_confidence", 0.0),
            summary=response.get("summary"),
        )

        logger.info(
            "Root cause analysis completed",
            hypothesis_count=len(hypotheses),
            root_cause=root_cause_result.root_cause,
            confidence=root_cause_result.confidence,
        )

        return {"root_cause": root_cause_result}

    def _build_analysis_context(
        self,
        question: str,
        intent: Any,
        raw_data: list[dict],
        cohort_analysis: Any,
        segmentation: Any,
        metric_values: list[Any],
        anomalies: list[dict],
    ) -> str:
        """Build comprehensive analysis context for the LLM."""
        sections = [
            f"## Investigation Question\n{question}",
        ]

        if intent:
            hypotheses_str = "\n".join(f"- {h}" for h in intent.hypotheses)
            sections.append(
                f"## Initial Hypotheses\n{hypotheses_str}"
            )

        # Metric summaries
        if metric_values:
            metrics_str = "\n".join([
                f"- {m.metric}: {m.value} (change: {m.change:+.2f}, {m.change_pct:+.1f}%)"
                for m in metric_values
            ])
            sections.append(f"## Key Metric Changes\n{metrics_str}")

        # Cohort insights
        if cohort_analysis and cohort_analysis.insights:
            insights_str = "\n".join([
                f"- {i.get('metric')}: {i.get('description', '')} (trend: {i.get('trend', 'unknown')})"
                for i in cohort_analysis.insights[:5]
            ])
            sections.append(f"## Cohort Analysis Insights\n{insights_str}")

        # Segment findings
        if segmentation:
            segments_str = "\n".join([
                f"- {s.name}: {s.user_count:,} users ({s.percentage:.1f}%), risk: {s.risk_level or 'unknown'}"
                for s in segmentation.segments[:5]
            ])
            sections.append(f"## User Segments\n{segments_str}")

        # Anomalies
        if anomalies:
            anomalies_str = "\n".join([
                f"- {a.get('metric')}: anomaly on {a.get('date')} (deviation: {a.get('deviation', 0):.1f}σ)"
                for a in anomalies[:5]
            ])
            sections.append(f"## Detected Anomalies\n{anomalies_str}")

        # Raw data summary (limit size)
        if raw_data:
            data_summary = []
            for dataset in raw_data[:3]:
                name = dataset.get("query_name", "Query")
                rows = dataset.get("data", [])
                if rows:
                    data_summary.append(f"**{name}** ({len(rows)} rows): {rows[:3]}")
            if data_summary:
                sections.append(f"## Data Evidence\n" + "\n".join(data_summary))

        sections.append(
            "\n## Task\nBased on all the evidence above, generate a comprehensive root cause analysis. "
            "Test each hypothesis against the data, calculate confidence scores, and identify the primary root cause."
        )

        return "\n\n".join(sections)