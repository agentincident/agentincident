"""CrewAI step callback for AgentIncident recording."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from ..recorder import Recorder


def crewai_step_callback(recorder: Recorder) -> Callable[..., None]:
    """Create a CrewAI step callback that records tool calls.

    Usage:
        from agentincident import Recorder
        from agentincident.integrations._crewai import crewai_step_callback

        recorder = Recorder()
        callback = crewai_step_callback(recorder)
        # Pass callback to CrewAI task/agent config
    """
    def callback(step: Any) -> None:
        tool = getattr(step, "tool", "unknown")
        tool_input = getattr(step, "tool_input", {})
        observation = getattr(step, "observation", "")
        if not isinstance(tool_input, dict):
            tool_input = {"input": tool_input}
        if not isinstance(observation, dict):
            observation = {"output": observation}
        recorder.record(tool=tool, input=tool_input, output=observation)

    return callback
