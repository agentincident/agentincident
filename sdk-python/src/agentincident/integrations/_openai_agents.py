"""OpenAI Agents SDK hooks for AgentIncident recording."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..recorder import Recorder

try:
    from agents import RunHooks

    _HAS_OPENAI_AGENTS = True
except ImportError:
    _HAS_OPENAI_AGENTS = False

    class RunHooks:  # type: ignore[no-redef]
        pass


class AgentIncidentRunHooks(RunHooks):
    """OpenAI Agents SDK hooks that record tool calls via AgentIncident Recorder."""

    def __init__(self, recorder: Recorder) -> None:
        if not _HAS_OPENAI_AGENTS:
            raise ImportError(
                "openai-agents is required. "
                "Install with: pip install agentincident[openai-agents]"
            )
        self.recorder = recorder
        self._pending: dict[str, dict[str, Any]] = {}

    async def on_tool_start(
        self, context: Any, agent: Any, tool: Any
    ) -> None:
        tool_name = getattr(tool, "name", str(tool))
        tool_input = getattr(tool, "input", {})
        if not isinstance(tool_input, dict):
            tool_input = {"input": tool_input}
        self._pending[tool_name] = {
            "input": tool_input,
            "start": datetime.now(timezone.utc),
        }

    async def on_tool_end(
        self, context: Any, agent: Any, tool: Any, result: Any
    ) -> None:
        tool_name = getattr(tool, "name", str(tool))
        pending = self._pending.pop(tool_name, None)
        start = pending["start"] if pending else datetime.now(timezone.utc)
        elapsed = int(
            (datetime.now(timezone.utc) - start).total_seconds() * 1000
        )
        input_data = pending["input"] if pending else {}
        output_data = result if isinstance(result, dict) else {"result": str(result)}
        self.recorder.record(
            tool=tool_name,
            input=input_data,
            output=output_data,
            duration_ms=elapsed,
        )
