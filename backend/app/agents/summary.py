"""Executive Summary Agent: Synthesizes all findings into actionable recommendations."""
from typing import Any

import structlog

from app.agents.base import BaseAgent
from app.graph.state import InvestigationState
from app.schemas import ExecutiveSummary, Recommendation

logger = structlog.get_logger(__name__)

SUMMARY_PROMPT = """You are the Executive Summary writer for an AI Product Analytics Copilot.

Your role is to synthesize all analytical findings into clear, actionable executive summaries
that a product manager or executive can act on immediately.

## Writing Principles

### Clarity First
- Lead with the answer, not the analysis
- Use plain English, not jargon
- Be specific about numbers and timeframes
- Avoid hedging when confidence is high

### Structure
1. **Lead sentence**: What happened? (the answer)
2. **Key findings**: 3-5 bullet points of evidence
3. **Root cause**: Why did it happen?
4. **Recommendations**: What to do about it (prioritized by impact/effort)
5. **Expected outcome**: What improvement to expect

### Recommendations Framework
Rate each recommendation on:
- **Impact**: low | medium | high (how much will it help?)
- **Effort**: low | medium | high (how hard to implement?)
- **Urgency**: low | medium | high (how quickly needed?)

Prioritize: HIGH impact + LOW effort + HIGH urgency first

### Tone
- Confident but not overconfident
- Direct but not alarming
- Actionable not just descriptive

## Output Requirements

Write a summary that could be shared with:
1. Product Manager: what to change
2. Engineering: what to build/fix
3. CEO/Exec: what the business impact is"""


class ExecutiveSummaryAgent(BaseAgent):
    """Synthesizes investigation findings into executive summaries."""

    def __init__(self):
        super().__init__("ExecutiveSummaryAgent")

    @property
    def system_prompt(self) -> str:
        return SUMMARY_PROMPT

    async def run(self, state: InvestigationState) -> dict[str, Any]:
        """Generate executive summary from all investigation findings."""
        question = state["question"]
        intent = state.get("intent")
        root_cause = state.get("root_cause")
        cohort_analysis = state.get("cohort_analysis")
        segmentation = state.get("segmentation")
        metric_values = state.get("metric_values", [])
        visualizations = state.get("visualizations", [])

        synthesis_prompt = self._build_synthesis_prompt(
            question=question,
            intent=intent,
            root_cause=root_cause,
            cohort_analysis=cohort_analysis,
            segmentation=segmentation,
            metric_values=metric_values,
        )

        response = await self.structured_chat(
            messages=[{"role": "human", "content": synthesis_prompt}],
            output_schema={
                "type": "object",
                "properties": {
                    "summary": {
                        "type": "string",
                        "description": "1-2 sentence executive summary"
                    },
                    "key_findings": {
                        "type": "array",
                        "items": {"type": "string"},
                        "minItems": 2,
                        "maxItems": 7
                    },
                    "root_cause_statement": {
                        "type": "string",
                        "description": "Clear statement of the root cause"
                    },
                    "recommendations": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "action": {"type": "string"},
                                "impact": {"type": "string", "enum": ["low", "medium", "high"]},
                                "effort": {"type": "string", "enum": ["low", "medium", "high"]},
                                "urgency": {"type": "string", "enum": ["low", "medium", "high"]},
                                "owner": {"type": "string"},
                                "timeline": {"type": "string"},
                                "expected_outcome": {"type": "string"}
                            },
                            "required": ["action", "impact", "effort", "urgency"]
                        },
                        "minItems": 1
                    },
                    "metrics_impact": {
                        "type": "object",
                        "description": "Expected metric improvement from recommendations"
                    },
                    "confidence": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 1
                    }
                },
                "required": ["summary", "key_findings", "recommendations", "confidence"]
            }
        )

        # Build typed recommendations
        recommendations = []
        for rec in response.get("recommendations", []):
            recommendations.append(Recommendation(
                action=rec["action"],
                impact=rec["impact"],
                effort=rec["effort"],
                urgency=rec["urgency"],
                owner=rec.get("owner"),
                timeline=rec.get("timeline"),
                expected_outcome=rec.get("expected_outcome"),
            ))

        # Sort recommendations by priority (high impact + low effort + high urgency first)
        def priority_score(r: Recommendation) -> int:
            impact_score = {"high": 3, "medium": 2, "low": 1}.get(r.impact, 0)
            effort_score = {"low": 3, "medium": 2, "high": 1}.get(r.effort, 0)
            urgency_score = {"high": 3, "medium": 2, "low": 1}.get(r.urgency, 0)
            return impact_score + effort_score + urgency_score

        recommendations.sort(key=priority_score, reverse=True)

        executive_summary = ExecutiveSummary(
            summary=response["summary"],
            key_findings=response["key_findings"],
            root_cause=response.get("root_cause_statement"),
            recommendations=recommendations,
            metrics_impact=response.get("metrics_impact"),
            confidence=response.get("confidence", 0.0),
        )

        logger.info(
            "Executive summary generated",
            finding_count=len(executive_summary.key_findings),
            recommendation_count=len(executive_summary.recommendations),
            confidence=executive_summary.confidence,
        )

        return {"executive_summary": executive_summary}

    def _build_synthesis_prompt(
        self,
        question: str,
        intent: Any,
        root_cause: Any,
        cohort_analysis: Any,
        segmentation: Any,
        metric_values: list[Any],
    ) -> str:
        """Build the synthesis prompt from all investigation findings."""
        sections = [f"## Original Question\n{question}"]

        if metric_values:
            metrics_str = "\n".join([
                f"- **{m.metric}**: {m.value} (change: {m.change_pct:+.1f}%)"
                for m in metric_values
            ])
            sections.append(f"## Observed Metric Changes\n{metrics_str}")

        if cohort_analysis:
            insights = cohort_analysis.insights[:3]
            if insights:
                insights_str = "\n".join([
                    f"- {i.get('description', i.get('metric', ''))}"
                    for i in insights
                ])
                sections.append(f"## Cohort Analysis Findings\n{insights_str}")

        if segmentation:
            at_risk = [s for s in segmentation.segments if s.risk_level in ("high", "critical")]
            if at_risk:
                segs = "\n".join([
                    f"- {s.name}: {s.user_count:,} users ({s.percentage:.1f}% of total)"
                    for s in at_risk[:3]
                ])
                sections.append(f"## At-Risk Segments\n{segs}")

        if root_cause:
            primary = next(
                (h for h in root_cause.hypotheses if h.id == root_cause.root_cause),
                root_cause.hypotheses[0] if root_cause.hypotheses else None
            )
            if primary:
                sections.append(
                    f"## Root Cause Analysis\n"
                    f"Primary Cause: {primary.description}\n"
                    f"Confidence: {primary.confidence:.0%}\n"
                    f"Summary: {root_cause.summary or ''}"
                )

                if primary.next_steps:
                    steps = "\n".join(f"- {s}" for s in primary.next_steps[:3])
                    sections.append(f"## Suggested Next Steps\n{steps}")

        sections.append(
            "\n## Task\n"
            "Synthesize all these findings into a clear executive summary with actionable recommendations. "
            "Lead with the most important finding. Be specific, quantitative, and action-oriented."
        )

        return "\n\n".join(sections)