"""Visualization Agent: Creates appropriate chart specifications for findings."""
import json
from typing import Any
from uuid import uuid4

import structlog

from app.agents.base import BaseAgent
from app.graph.state import InvestigationState
from app.schemas import Visualization, ChartConfig, ChartType, DataPoint

logger = structlog.get_logger(__name__)

VISUALIZATION_PROMPT = """You are the Visualization Designer for an AI Product Analytics Copilot.

Your role is to create appropriate chart specifications that best communicate analytical findings.

## Chart Selection Guidelines

| Data Type | Best Chart |
|-----------|------------|
| Time series trend | Line chart |
| Category comparison | Bar chart |
| Cohort retention | Heatmap |
| Distribution | Histogram |
| Conversion funnel | Funnel chart |
| Part of whole | Donut/Pie |
| Correlation | Scatter plot |
| Revenue over time | Area chart |

## Vega-Lite Specifications

Always output Vega-Lite specs. Key structure:
```json
{
  "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
  "title": "Chart Title",
  "mark": "line",
  "encoding": {
    "x": {"field": "date", "type": "temporal"},
    "y": {"field": "value", "type": "quantitative"},
    "color": {"field": "segment", "type": "nominal"}
  }
}
```

## Color Guidelines
- Use accessible color palettes
- Red/orange for negative trends, green/blue for positive
- Consistent colors across related charts

## Annotation Guidelines
- Mark significant events (feature launches, incidents)
- Highlight anomalies
- Show confidence intervals where relevant"""


class VisualizationAgent(BaseAgent):
    """Creates chart specifications for investigation findings."""

    def __init__(self):
        super().__init__("VisualizationAgent")

    @property
    def system_prompt(self) -> str:
        return VISUALIZATION_PROMPT

    async def run(self, state: InvestigationState) -> dict[str, Any]:
        """Generate visualizations for all findings."""
        visualizations = []

        # Generate retention curve if cohort analysis available
        if state.get("cohort_analysis"):
            viz = await self._create_retention_curve(state)
            if viz:
                visualizations.append(viz)

        # Generate metric trend charts
        if state.get("raw_data"):
            trend_viz = await self._create_trend_chart(state)
            if trend_viz:
                visualizations.append(trend_viz)

        # Generate segment comparison if segmentation available
        if state.get("segmentation"):
            seg_viz = await self._create_segment_chart(state)
            if seg_viz:
                visualizations.append(seg_viz)

        logger.info("Visualizations generated", count=len(visualizations))

        return {"visualizations": visualizations}

    async def _create_retention_curve(self, state: InvestigationState) -> Visualization | None:
        """Create a retention curve visualization."""
        cohort_analysis = state.get("cohort_analysis")
        if not cohort_analysis or not cohort_analysis.cohorts:
            return None

        # Build cohort data for visualization
        chart_data = []
        for cohort in cohort_analysis.cohorts[-6:]:  # Last 6 cohorts
            for i, ret_rate in enumerate(cohort.retention):
                chart_data.append({
                    "cohort": cohort.period,
                    "week": i,
                    "retention": round(ret_rate * 100, 1),
                })

        vega_spec = {
            "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
            "title": "Cohort Retention Curves",
            "width": 600,
            "height": 400,
            "data": {"values": chart_data},
            "mark": {"type": "line", "point": True},
            "encoding": {
                "x": {
                    "field": "week",
                    "type": "ordinal",
                    "title": "Weeks Since Signup",
                    "axis": {"labelExpr": "'Week ' + datum.label"}
                },
                "y": {
                    "field": "retention",
                    "type": "quantitative",
                    "title": "Retention Rate (%)",
                    "scale": {"domain": [0, 100]}
                },
                "color": {
                    "field": "cohort",
                    "type": "nominal",
                    "title": "Cohort"
                },
                "tooltip": [
                    {"field": "cohort", "type": "nominal", "title": "Cohort"},
                    {"field": "week", "type": "ordinal", "title": "Week"},
                    {"field": "retention", "type": "quantitative", "title": "Retention %", "format": ".1f"},
                ]
            }
        }

        return Visualization(
            id=str(uuid4()),
            type=ChartType.LINE,
            title="Cohort Retention Curves",
            data=chart_data,
            config=ChartConfig(
                type=ChartType.LINE,
                title="Cohort Retention Curves",
                x_axis="Weeks Since Signup",
                y_axis="Retention Rate (%)",
                show_legend=True,
            ),
            vega_spec=vega_spec,
        )

    async def _create_trend_chart(self, state: InvestigationState) -> Visualization | None:
        """Create a trend line chart for the primary metric."""
        raw_data = state.get("raw_data", [])
        if not raw_data:
            return None

        # Find time series data
        time_series_data = None
        for dataset in raw_data:
            data = dataset.get("data", [])
            if data and any(k in str(data[0].keys()).lower() for k in ["date", "week", "month"]):
                time_series_data = dataset
                break

        if not time_series_data:
            return None

        data = time_series_data.get("data", [])
        chart_data = data[:90]  # Limit to 90 data points

        # Determine date field and value field
        first_row = chart_data[0] if chart_data else {}
        date_field = next((k for k in first_row.keys() if any(
            t in k.lower() for t in ["date", "week", "month", "day"]
        )), None)
        value_field = next((k for k in first_row.keys() if k != date_field), None)

        if not date_field or not value_field:
            return None

        vega_spec = {
            "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
            "title": f"{value_field.replace('_', ' ').title()} Over Time",
            "width": 600,
            "height": 300,
            "data": {"values": chart_data},
            "mark": {"type": "area", "opacity": 0.4, "line": True},
            "encoding": {
                "x": {"field": date_field, "type": "temporal", "title": "Date"},
                "y": {"field": value_field, "type": "quantitative", "title": value_field.replace("_", " ").title()},
                "tooltip": [
                    {"field": date_field, "type": "temporal", "title": "Date"},
                    {"field": value_field, "type": "quantitative", "title": value_field.replace("_", " ").title()},
                ]
            }
        }

        return Visualization(
            id=str(uuid4()),
            type=ChartType.AREA,
            title=f"{value_field.replace('_', ' ').title()} Trend",
            data=chart_data,
            config=ChartConfig(
                type=ChartType.AREA,
                title=f"{value_field.replace('_', ' ').title()} Trend",
                x_axis="Date",
                y_axis=value_field.replace("_", " ").title(),
                show_legend=False,
            ),
            vega_spec=vega_spec,
        )

    async def _create_segment_chart(self, state: InvestigationState) -> Visualization | None:
        """Create a bar chart for segment comparison."""
        segmentation = state.get("segmentation")
        if not segmentation or not segmentation.segments:
            return None

        chart_data = [
            {
                "segment": s.name,
                "users": s.user_count,
                "percentage": round(s.percentage, 1),
                "risk": s.risk_level or "unknown",
            }
            for s in segmentation.segments
        ]

        vega_spec = {
            "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
            "title": "User Segments",
            "width": 500,
            "height": 300,
            "data": {"values": chart_data},
            "mark": "bar",
            "encoding": {
                "x": {"field": "segment", "type": "nominal", "title": "Segment", "sort": "-y"},
                "y": {"field": "users", "type": "quantitative", "title": "Users"},
                "color": {
                    "field": "risk",
                    "type": "nominal",
                    "scale": {
                        "domain": ["low", "medium", "high", "critical"],
                        "range": ["#22c55e", "#f59e0b", "#ef4444", "#7f1d1d"]
                    },
                    "title": "Risk Level"
                },
                "tooltip": [
                    {"field": "segment", "type": "nominal", "title": "Segment"},
                    {"field": "users", "type": "quantitative", "title": "Users"},
                    {"field": "percentage", "type": "quantitative", "title": "% of Total"},
                    {"field": "risk", "type": "nominal", "title": "Risk Level"},
                ]
            }
        }

        return Visualization(
            id=str(uuid4()),
            type=ChartType.BAR,
            title="User Segment Distribution",
            data=chart_data,
            config=ChartConfig(
                type=ChartType.BAR,
                title="User Segment Distribution",
                x_axis="Segment",
                y_axis="Users",
                show_legend=True,
            ),
            vega_spec=vega_spec,
        )