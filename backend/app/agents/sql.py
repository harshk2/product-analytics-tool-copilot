"""SQL Agent: Generates, validates, and executes safe SQL queries."""
import re
from typing import Any

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import BaseAgent
from app.config import settings
from app.graph.state import InvestigationState
from app.schemas import SQLGenerationResult

logger = structlog.get_logger(__name__)

# ─── Database Schema Context ───────────────────────────────────────────────────

DB_SCHEMA_CONTEXT = """
## Available Database Tables

### users
Columns: id (UUID), email, created_at, deleted_at, country (2-char),
         acquisition_source, acquisition_channel, company_name, plan
         (free/starter/pro/enterprise), metadata (JSONB)

### events
Columns: id (BIGINT), user_id (FK→users), session_id, event_type,
         event_category, event_action, platform, device_type, properties (JSONB),
         occurred_at

Common event_types: 'page_view', 'feature_used', 'button_clicked', 'signup',
                   'login', 'payment_initiated', 'payment_completed', 'subscription_created'

### subscriptions
Columns: id (UUID), user_id (FK→users), plan, status
         (active/trialing/past_due/canceled/paused/expired), billing_cycle (monthly/annual),
         base_amount_cents, discount_cents, started_at, current_period_starts_at,
         current_period_ends_at, cancelled_at, cancellation_reason

### payments
Columns: id (UUID), subscription_id (FK), user_id (FK→users), amount_cents,
         currency, status (pending/succeeded/failed/refunded/disputed),
         payment_method, failure_code, failure_message, risk_score,
         is_flagged, created_at, processed_at, failed_at

### feature_flags
Columns: id (UUID), name, description, enabled_at, disabled_at,
         rollout_percentage, created_at

## Important Notes

- All monetary values are in **cents** (divide by 100 for dollars)
- Timestamps are TIMESTAMPTZ (timezone-aware)
- Use date_trunc() for period aggregations
- Use DISTINCT users for unique user counts
- The `metadata` column is JSONB - use -> and ->> operators
- Filter deleted_at IS NULL for active users
"""

SQL_AGENT_PROMPT = f"""You are the SQL Analyst for an AI Product Analytics Copilot.

Your role is to generate safe, optimized SQL queries to retrieve analytics data.

{DB_SCHEMA_CONTEXT}

## Query Safety Rules (STRICTLY ENFORCED)

ALLOWED: SELECT statements only
BLOCKED: INSERT, UPDATE, DELETE, DROP, TRUNCATE, ALTER, CREATE, GRANT, REVOKE

## Query Guidelines

1. Always use aliases for readability
2. Include appropriate WHERE clauses to limit data
3. Use CTEs (WITH clauses) for complex queries
4. Prefer window functions over subqueries when possible
5. Always include ORDER BY for time series data
6. Use LIMIT to prevent runaway queries (max {settings.SQL_MAX_ROWS})
7. Round floating point values to 4 decimal places

## Common Analytics Patterns

### Retention Rate
```sql
WITH cohort AS (
    SELECT user_id, date_trunc('week', created_at) AS cohort_week
    FROM users
    WHERE created_at BETWEEN :start AND :end
),
activity AS (
    SELECT DISTINCT user_id, date_trunc('week', occurred_at) AS active_week
    FROM events
)
SELECT
    c.cohort_week,
    COUNT(DISTINCT c.user_id) AS cohort_size,
    COUNT(DISTINCT a.user_id) AS retained_users,
    ROUND(COUNT(DISTINCT a.user_id)::DECIMAL / COUNT(DISTINCT c.user_id), 4) AS retention_rate
FROM cohort c
LEFT JOIN activity a ON c.user_id = a.user_id
    AND a.active_week = c.cohort_week + INTERVAL '1 week'
GROUP BY c.cohort_week
ORDER BY c.cohort_week;
```

### MRR Trend
```sql
SELECT
    date_trunc('month', created_at) AS month,
    SUM(amount_cents) / 100.0 AS mrr
FROM payments
WHERE status = 'succeeded'
    AND created_at >= NOW() - INTERVAL '12 months'
GROUP BY 1
ORDER BY 1;
```

### Funnel Analysis
```sql
SELECT
    event_type,
    COUNT(DISTINCT user_id) AS unique_users,
    COUNT(*) AS total_events
FROM events
WHERE event_type IN ('signup', 'onboarding_started', 'feature_used', 'payment_initiated')
    AND occurred_at >= NOW() - INTERVAL '30 days'
GROUP BY event_type
ORDER BY unique_users DESC;
```"""


# ─── SQL Validator ─────────────────────────────────────────────────────────────

class SQLValidator:
    """Validates SQL queries for safety before execution."""

    BLOCKED_KEYWORDS = frozenset([
        "INSERT", "UPDATE", "DELETE", "DROP", "TRUNCATE",
        "ALTER", "CREATE", "GRANT", "REVOKE", "EXECUTE",
        "EXEC", "CALL", "DO", "COPY", "VACUUM", "ANALYZE",
    ])

    @classmethod
    def validate(cls, query: str) -> tuple[bool, list[str]]:
        """Validate a SQL query.

        Returns:
            Tuple of (is_safe, list_of_violations).
        """
        errors = []
        upper_query = query.upper().strip()

        # Check for blocked keywords
        # Use word boundaries to avoid false positives
        for keyword in cls.BLOCKED_KEYWORDS:
            pattern = r'\b' + keyword + r'\b'
            if re.search(pattern, upper_query):
                errors.append(f"Query contains blocked operation: {keyword}")

        # Must start with SELECT or WITH (for CTEs)
        if not (upper_query.startswith("SELECT") or upper_query.startswith("WITH")):
            errors.append("Query must start with SELECT or WITH (CTE)")

        # Check for multiple statements
        # Remove content in quotes first to avoid false positives
        cleaned = re.sub(r"'[^']*'", "''", query)
        statements = [s.strip() for s in cleaned.split(";") if s.strip()]
        if len(statements) > 1:
            errors.append("Multiple statements are not allowed")

        # Warn about missing LIMIT
        if "LIMIT" not in upper_query:
            errors.append("Query should include a LIMIT clause")

        return len(errors) == 0, errors


# ─── SQL Agent ─────────────────────────────────────────────────────────────────

class SQLAgent(BaseAgent):
    """Generates, validates, and executes safe SQL queries."""

    def __init__(self, db: AsyncSession):
        super().__init__("SQLAgent")
        self.db = db
        self.validator = SQLValidator()

    @property
    def system_prompt(self) -> str:
        return SQL_AGENT_PROMPT

    async def run(self, state: InvestigationState) -> dict[str, Any]:
        """Generate and execute SQL queries for the investigation."""
        intent = state.get("intent")
        if not intent:
            return {"errors": ["SQLAgent: No intent provided"]}

        question = state["question"]
        metrics = intent.primary_metrics
        time_range = intent.time_range or {}

        # Determine lookback period
        lookback_days = time_range.get("lookback_days", 30)

        # Generate queries for each metric
        query_results = []
        raw_data = []

        # Generate a query for the primary investigation
        query_prompt = self._build_query_prompt(
            question=question,
            metrics=metrics,
            lookback_days=lookback_days,
            intent_type=intent.intent_type.value,
            context=state.get("user_context", {}),
        )

        try:
            sql_response = await self.structured_chat(
                messages=[{"role": "human", "content": query_prompt}],
                output_schema={
                    "type": "object",
                    "properties": {
                        "queries": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string"},
                                    "description": {"type": "string"},
                                    "sql": {"type": "string"},
                                    "metric": {"type": "string"}
                                },
                                "required": ["name", "sql"]
                            }
                        }
                    },
                    "required": ["queries"]
                }
            )

            queries = sql_response.get("queries", [])

            for query_spec in queries[:settings.SQL_MAX_QUERIES_PER_INVESTIGATION]:
                result = await self._execute_query(
                    name=query_spec.get("name", "query"),
                    query=query_spec["sql"],
                    description=query_spec.get("description", ""),
                )
                query_results.append(result)

                if result.errors:
                    logger.warning(
                        "Query failed",
                        query_name=query_spec.get("name"),
                        errors=result.errors,
                    )
                else:
                    raw_data.append({
                        "query_name": query_spec.get("name"),
                        "metric": query_spec.get("metric"),
                        "data": result.results,
                        "row_count": result.row_count,
                    })

        except Exception as e:
            logger.error("SQL generation failed", error=str(e), exc_info=True)
            return {
                "errors": [f"SQL generation error: {str(e)}"],
                "generated_queries": [],
                "raw_data": [],
            }

        logger.info(
            "SQL queries completed",
            queries_generated=len(query_results),
            queries_successful=len([q for q in query_results if not q.errors]),
        )

        return {
            "generated_queries": query_results,
            "raw_data": raw_data,
        }

    def _build_query_prompt(
        self,
        question: str,
        metrics: list[str],
        lookback_days: int,
        intent_type: str,
        context: dict[str, Any],
    ) -> str:
        """Build the prompt for SQL generation."""
        filter_context = ""
        if context.get("filters"):
            filter_context = f"\nApply these additional filters: {context['filters']}"

        return f"""Generate SQL queries to investigate this business question:

**Question**: {question}

**Intent Type**: {intent_type}
**Primary Metrics**: {', '.join(metrics)}
**Lookback Period**: Last {lookback_days} days{filter_context}

Generate 2-4 SQL queries that will help answer this question. Each query should:
1. Return useful analytics data for the investigation
2. Be optimized for performance
3. Include appropriate date filters
4. Use meaningful column aliases

The queries should collectively provide data for:
- The current state of the primary metrics
- Time series trends to identify when the change occurred
- Segmentation to identify affected user groups"""

    async def _execute_query(
        self,
        name: str,
        query: str,
        description: str = "",
    ) -> SQLGenerationResult:
        """Execute a single query and return results."""
        import time

        # Validate first
        is_safe, violations = self.validator.validate(query)

        if not is_safe:
            # For validation failures, return without executing
            return SQLGenerationResult(
                query=query,
                is_safe=False,
                results=[],
                errors=violations,
            )

        # Execute the query
        start_time = time.monotonic()
        try:
            result = await self.db.execute(
                text(query).execution_options(
                    timeout=settings.SQL_QUERY_TIMEOUT_MS / 1000
                )
            )
            elapsed_ms = (time.monotonic() - start_time) * 1000

            # Convert to list of dicts
            columns = list(result.keys())
            rows = result.fetchmany(settings.SQL_MAX_ROWS)
            results = [dict(zip(columns, row, strict=False)) for row in rows]

            return SQLGenerationResult(
                query=query,
                is_safe=True,
                estimated_rows=len(results),
                execution_time_ms=elapsed_ms,
                results=results,
            )

        except Exception as e:
            elapsed_ms = (time.monotonic() - start_time) * 1000
            return SQLGenerationResult(
                query=query,
                is_safe=True,  # Safe but execution failed
                execution_time_ms=elapsed_ms,
                results=[],
                errors=[f"Query execution error: {str(e)}"],
            )
