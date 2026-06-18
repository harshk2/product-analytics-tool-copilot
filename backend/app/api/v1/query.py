"""Query API endpoints for direct SQL execution."""
import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.sql import SQLValidator
from app.db.session import get_db
from app.schemas import QueryRequest, QueryResult

logger = structlog.get_logger(__name__)
router = APIRouter()

validator = SQLValidator()


@router.post(
    "/",
    response_model=QueryResult,
    summary="Execute analytics query",
    description="Ask a data question in natural language and get query results",
)
async def execute_query(
    request: QueryRequest,
    db: AsyncSession = Depends(get_db),
):
    """Execute a natural language analytics query."""
    import time

    from app.agents.sql import SQLAgent

    sql_agent = SQLAgent(db)

    # Use SQL Agent to generate the query
    try:
        sql_response = await sql_agent.structured_chat(
            messages=[{
                "role": "human",
                "content": f"Generate a single SQL query to answer: {request.question}"
            }],
            output_schema={
                "type": "object",
                "properties": {
                    "sql": {"type": "string"},
                    "explanation": {"type": "string"}
                },
                "required": ["sql"]
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Failed to generate query: {str(e)}",
        ) from e

    sql = sql_response.get("sql", "")
    explanation = sql_response.get("explanation")

    # Validate
    is_safe, violations = validator.validate(sql)
    if not is_safe:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Query validation failed: {'; '.join(violations)}",
        )

    # Execute
    start_time = time.monotonic()
    try:
        result = await db.execute(text(sql))
        elapsed_ms = (time.monotonic() - start_time) * 1000

        columns = list(result.keys())
        rows = result.fetchmany(1000)
        results = [dict(zip(columns, row, strict=False)) for row in rows]

        return QueryResult(
            query=sql,
            results=results,
            row_count=len(results),
            execution_time_ms=elapsed_ms,
            columns=columns,
            explanation=explanation,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Query execution failed: {str(e)}",
        ) from e


@router.post(
    "/validate",
    summary="Validate a SQL query",
    description="Check if a SQL query is safe to execute",
)
async def validate_query(body: dict):
    """Validate a SQL query for safety."""
    sql = body.get("sql", "")
    is_safe, violations = validator.validate(sql)
    return {
        "is_safe": is_safe,
        "violations": violations,
    }
