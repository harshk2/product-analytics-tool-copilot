"""Integration tests for API endpoints."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
class TestHealthEndpoint:
    async def test_health_check_returns_200(self, client):
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data


@pytest.mark.asyncio
class TestChatEndpoint:
    """Tests for the streaming chat endpoint."""

    async def test_chat_returns_event_stream(self, client, mock_db):
        """POST /api/v1/chat/ should return SSE stream."""
        # Mock the investigation graph
        async def mock_stream(*args, **kwargs):
            yield {"type": "investigation_start", "data": {"investigation_id": "test-123"}}
            yield {"type": "thinking", "agent": "intent", "message": "Analyzing..."}
            yield {"type": "complete", "data": {"investigation_id": "test-123"}}

        with patch("app.api.v1.chat.InvestigationGraph") as MockGraph:
            instance = MockGraph.return_value
            instance.stream = mock_stream

            # Mock DB operations
            mock_investigation = MagicMock()
            mock_investigation.id = "test-123"
            mock_db.add = MagicMock()
            mock_db.flush = AsyncMock()

            response = await client.post(
                "/api/v1/chat/",
                json={
                    "message": "Why did retention drop last week?",
                    "session_id": "test-session"
                }
            )

        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")

    async def test_chat_requires_message(self, client):
        """POST /api/v1/chat/ should reject empty messages."""
        response = await client.post(
            "/api/v1/chat/",
            json={"message": ""}
        )
        assert response.status_code == 422  # Validation error

    async def test_chat_rejects_too_long_message(self, client):
        """POST /api/v1/chat/ should reject messages over 2000 chars."""
        response = await client.post(
            "/api/v1/chat/",
            json={"message": "x" * 2001}
        )
        assert response.status_code == 422


@pytest.mark.asyncio
class TestDashboardEndpoint:
    """Tests for the dashboard endpoint."""

    async def test_dashboard_returns_kpis(self, client, mock_db):
        """GET /api/v1/dashboard/ should return dashboard data."""
        # Mock DB query results
        mock_result = MagicMock()
        mock_result.scalar.return_value = 100
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)

        response = await client.get("/api/v1/dashboard/")
        assert response.status_code == 200
        data = response.json()
        assert "kpis" in data
        assert "alerts" in data
        assert "recent_investigations" in data
        assert "updated_at" in data


@pytest.mark.asyncio
class TestMemoryEndpoint:
    """Tests for memory/history endpoint."""

    async def test_list_all_investigations_returns_200(self, client, mock_db):
        """GET /api/v1/memory/ should return investigation history."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)

        response = await client.get("/api/v1/memory/")
        assert response.status_code == 200
        data = response.json()
        assert "investigations" in data
        assert "total" in data

    async def test_similar_search_returns_results(self, client, mock_db):
        """GET /api/v1/memory/similar should search past investigations."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)

        response = await client.get(
            "/api/v1/memory/similar",
            params={"question": "Why did retention drop?"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert "query" in data


@pytest.mark.asyncio
class TestQueryEndpoint:
    """Tests for the direct SQL query endpoint."""

    async def test_query_requires_question(self, client):
        """POST /api/v1/query/ should reject empty questions."""
        response = await client.post(
            "/api/v1/query/",
            json={"question": ""}
        )
        assert response.status_code == 422
