"""Pytest configuration and shared fixtures."""
import asyncio
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient

from app.main import app


@pytest.fixture
def mock_db():
    """Mock SQLAlchemy async session."""
    db = AsyncMock()
    db.execute = AsyncMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.add = MagicMock()
    return db


@pytest.fixture
def mock_gemini_response():
    """Mock Gemini LLM response for structured output."""
    def _make_response(data: dict) -> MagicMock:
        import json
        mock = MagicMock()
        mock.content = json.dumps(data)
        return mock
    return _make_response


@pytest.fixture
def mock_llm(mock_gemini_response):
    """Mock LangChain ChatGoogleGenerativeAI client."""
    with patch("app.agents.base.ChatGoogleGenerativeAI") as mock_cls:
        mock_instance = MagicMock()
        mock_instance.ainvoke = AsyncMock()
        mock_cls.return_value = mock_instance
        yield mock_instance


@pytest_asyncio.fixture
async def client(mock_db):
    """Async HTTP test client with mocked database."""
    from app.db.session import get_db
    app.dependency_overrides[get_db] = lambda: mock_db
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
def sample_investigation_state():
    """Sample investigation state for agent testing."""
    from app.graph.state import create_initial_state
    return create_initial_state(
        investigation_id="test-inv-001",
        question="Why did retention drop last week?",
        session_id="test-session",
        user_context={"filters": {}},
    )
