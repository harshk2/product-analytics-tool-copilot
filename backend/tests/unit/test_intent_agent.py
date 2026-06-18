"""Unit tests for IntentAgent — LLM output parsing and state updates."""
import json
from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.mark.asyncio
class TestIntentAgent:
    """Tests for IntentAgent intent parsing."""

    def _make_agent_with_mock_llm(self, llm_response: dict):
        """Create an IntentAgent with a mocked LLM that returns the given response."""
        from app.agents.intent import IntentAgent

        agent = IntentAgent.__new__(IntentAgent)
        agent.name = "IntentAgent"

        mock_llm = MagicMock()
        mock_llm.ainvoke = AsyncMock(return_value=MagicMock(
            content=json.dumps(llm_response)
        ))
        agent.llm = mock_llm
        return agent

    async def test_retention_question_parsed_correctly(self, sample_investigation_state):
        """IntentAgent should identify retention investigation from question."""
        mock_response = {
            "intent_type": "retention_investigation",
            "primary_metrics": ["weekly_retention_rate", "cohort_retention"],
            "time_range": {
                "focus": "last_week",
                "comparison": "previous_week",
                "lookback_days": 14
            },
            "dimensions": ["plan", "acquisition_source"],
            "hypotheses": [
                "Feature change affecting engagement",
                "Payment issue causing churn",
                "Competitor activity"
            ],
            "required_analyses": ["cohort_retention", "segment_comparison"],
            "priority": "high",
            "reasoning": "Retention drop requires cohort analysis to identify affected groups"
        }

        agent = self._make_agent_with_mock_llm(mock_response)
        result = await agent.run(sample_investigation_state)

        assert "intent" in result
        intent = result["intent"]
        assert intent.intent_type.value == "retention_investigation"
        assert "weekly_retention_rate" in intent.primary_metrics
        assert len(intent.hypotheses) >= 2
        assert intent.priority == "high"

    async def test_payment_question_parsed_correctly(self, sample_investigation_state):
        """IntentAgent should identify payment failure investigation."""
        state = {**sample_investigation_state, "question": "Why are payment failures increasing?"}
        mock_response = {
            "intent_type": "payment_failure_investigation",
            "primary_metrics": ["payment_failure_rate", "payment_success_rate"],
            "time_range": {"focus": "last_week", "comparison": "previous_week", "lookback_days": 14},
            "dimensions": ["payment_method", "country"],
            "hypotheses": [
                "New payment processor issue",
                "Increased fraud attempts",
                "Card expiration wave"
            ],
            "required_analyses": ["revenue_analysis", "anomaly_detection"],
            "priority": "critical",
            "reasoning": "Payment failures need immediate revenue analysis"
        }

        agent = self._make_agent_with_mock_llm(mock_response)
        result = await agent.run(state)

        assert result["intent"].intent_type.value == "payment_failure_investigation"
        assert result["intent"].priority == "critical"

    async def test_revenue_question_parsed_correctly(self, sample_investigation_state):
        """IntentAgent should identify revenue investigation."""
        state = {
            **sample_investigation_state,
            "question": "Why did revenue decrease despite user growth?"
        }
        mock_response = {
            "intent_type": "revenue_investigation",
            "primary_metrics": ["mrr", "arr", "average_revenue_per_user"],
            "time_range": {"focus": "last_month", "comparison": "previous_month", "lookback_days": 60},
            "dimensions": ["plan", "billing_cycle"],
            "hypotheses": [
                "Plan downgrade wave",
                "Higher discount usage",
                "Free tier expansion with no conversion"
            ],
            "required_analyses": ["revenue_analysis", "segment_comparison"],
            "priority": "high",
            "reasoning": "Revenue despite user growth suggests monetization gap"
        }

        agent = self._make_agent_with_mock_llm(mock_response)
        result = await agent.run(state)

        intent = result["intent"]
        assert intent.intent_type.value == "revenue_investigation"
        assert "mrr" in intent.primary_metrics

    async def test_intent_with_user_context_filters(self, sample_investigation_state):
        """IntentAgent should incorporate user context filters."""
        state = {
            **sample_investigation_state,
            "user_context": {
                "filters": {"plan": "enterprise", "country": "US"}
            }
        }
        mock_response = {
            "intent_type": "retention_investigation",
            "primary_metrics": ["weekly_retention_rate"],
            "time_range": {"focus": "last_week", "comparison": "previous_week", "lookback_days": 14},
            "dimensions": ["plan"],
            "hypotheses": ["Enterprise contract renewal issues"],
            "required_analyses": ["cohort_retention"],
            "priority": "high",
            "reasoning": "Enterprise US retention focus"
        }

        agent = self._make_agent_with_mock_llm(mock_response)

        # Verify the LLM was invoked (context should be included in prompt)
        await agent.run(state)
        agent.llm.ainvoke.assert_called_once()

    async def test_intent_result_has_required_fields(self, sample_investigation_state):
        """IntentAgent result should always have required schema fields."""
        mock_response = {
            "intent_type": "general_analytics",
            "primary_metrics": ["dau"],
            "hypotheses": ["normal variation", "data issue"],
            "required_analyses": ["anomaly_detection"],
            "priority": "low",
        }

        agent = self._make_agent_with_mock_llm(mock_response)
        result = await agent.run(sample_investigation_state)

        assert "intent" in result
        intent = result["intent"]
        assert intent.intent_type is not None
        assert isinstance(intent.primary_metrics, list)
        assert isinstance(intent.hypotheses, list)
        assert len(intent.hypotheses) >= 1

    async def test_llm_json_parse_error_raises_value_error(self, sample_investigation_state):
        """IntentAgent should raise ValueError on invalid JSON from LLM."""
        from app.agents.intent import IntentAgent

        agent = IntentAgent.__new__(IntentAgent)
        agent.name = "IntentAgent"
        mock_llm = MagicMock()
        mock_llm.ainvoke = AsyncMock(return_value=MagicMock(
            content="This is not JSON at all"
        ))
        agent.llm = mock_llm

        with pytest.raises(ValueError, match="invalid JSON"):
            await agent.run(sample_investigation_state)
