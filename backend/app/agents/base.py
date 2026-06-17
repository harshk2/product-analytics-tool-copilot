"""Base agent class with common functionality."""
import time
from abc import ABC, abstractmethod
from typing import Any

import structlog
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage

from app.config import settings
from app.graph.state import InvestigationState

logger = structlog.get_logger(__name__)


class BaseAgent(ABC):
    """Base class for all investigation agents.

    Each agent:
    - Receives the full investigation state
    - Performs its specific analysis
    - Returns updated state
    - Logs its execution trace
    """

    def __init__(self, name: str):
        self.name = name
        self.llm = ChatGoogleGenerativeAI(
            model=settings.GEMINI_MODEL,
            google_api_key=settings.GEMINI_API_KEY,
            temperature=settings.GEMINI_TEMPERATURE,
            max_output_tokens=settings.GEMINI_MAX_TOKENS,
            convert_system_message_to_human=True,  # Gemini requires system msg merged into human
        )

    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """System prompt defining agent's role and behavior."""
        ...

    @abstractmethod
    async def run(self, state: InvestigationState) -> dict[str, Any]:
        """Execute the agent and return state updates.

        Args:
            state: Current investigation state.

        Returns:
            Dictionary of state fields to update.
        """
        ...

    async def invoke(self, state: InvestigationState) -> dict[str, Any]:
        """Wrapper around run() that adds tracing and error handling."""
        start_time = time.monotonic()
        logger.info(f"Agent starting", agent=self.name, investigation_id=state["investigation_id"])

        try:
            result = await self.run(state)
            elapsed_ms = (time.monotonic() - start_time) * 1000

            # Add to agent trace
            trace_entry = {
                "agent": self.name,
                "elapsed_ms": elapsed_ms,
                "status": "success",
                "timestamp": time.time(),
            }

            if "agent_trace" not in result:
                result["agent_trace"] = []
            result["agent_trace"].append(trace_entry)

            logger.info(
                "Agent completed",
                agent=self.name,
                elapsed_ms=elapsed_ms,
                investigation_id=state["investigation_id"],
            )

            return result

        except Exception as e:
            elapsed_ms = (time.monotonic() - start_time) * 1000
            error_msg = f"{self.name}: {str(e)}"

            logger.error(
                "Agent failed",
                agent=self.name,
                error=str(e),
                elapsed_ms=elapsed_ms,
                investigation_id=state["investigation_id"],
                exc_info=True,
            )

            return {
                "errors": [error_msg],
                "agent_trace": [{
                    "agent": self.name,
                    "elapsed_ms": elapsed_ms,
                    "status": "error",
                    "error": str(e),
                    "timestamp": time.time(),
                }]
            }

    @staticmethod
    def _extract_text(content: Any) -> str:
        """Extract plain text from LLM response content.

        Gemini can return content as either a plain string or a list
        of content blocks (e.g. [{"type": "text", "text": "..."}]).
        This handles both formats safely.
        """
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts = []
            for block in content:
                if isinstance(block, dict):
                    parts.append(block.get("text", ""))
                elif isinstance(block, str):
                    parts.append(block)
            return "".join(parts)
        return str(content)

    async def chat(
        self,
        messages: list[dict[str, str]],
        system_override: str | None = None,
    ) -> str:
        """Send messages to the LLM and return text response."""
        system = system_override or self.system_prompt

        langchain_messages = [SystemMessage(content=system)]
        for msg in messages:
            if msg["role"] == "human":
                langchain_messages.append(HumanMessage(content=msg["content"]))

        response = await self.llm.ainvoke(langchain_messages)
        return self._extract_text(response.content)

    async def structured_chat(
        self,
        messages: list[dict[str, str]],
        output_schema: dict[str, Any],
        system_override: str | None = None,
    ) -> dict[str, Any]:
        """Send messages and parse structured JSON response."""
        import json

        system = (system_override or self.system_prompt) + f"""

Always respond with valid JSON matching this schema:
{json.dumps(output_schema, indent=2)}

Do not include any text outside the JSON object."""

        response_text = await self.chat(messages, system_override=system)

        # Parse JSON, handling potential markdown code blocks
        text = response_text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            # Find the JSON content between code fences
            start = 1 if lines[0].startswith("```") else 0
            end = len(lines) - 1 if lines[-1] == "```" else len(lines)
            text = "\n".join(lines[start:end])

        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            logger.error(
                "Failed to parse LLM JSON response",
                agent=self.name,
                error=str(e),
                response_text=response_text[:500],
            )
            raise ValueError(f"LLM returned invalid JSON: {e}") from e