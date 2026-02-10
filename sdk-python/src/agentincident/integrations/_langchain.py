"""LangChain callback handler for AgentIncident recording."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any
from uuid import UUID

if TYPE_CHECKING:
    from ..recorder import Recorder

try:
    from langchain_core.callbacks import BaseCallbackHandler

    _HAS_LANGCHAIN = True
except ImportError:
    _HAS_LANGCHAIN = False
    # Provide a stub so the class definition doesn't fail at import time
    class BaseCallbackHandler:  # type: ignore[no-redef]
        pass


class AgentIncidentCallbackHandler(BaseCallbackHandler):
    """LangChain callback handler that records tool calls via AgentIncident Recorder."""

    def __init__(self, recorder: Recorder) -> None:
        if not _HAS_LANGCHAIN:
            raise ImportError(
                "langchain-core is required. "
                "Install with: pip install agentincident[langchain]"
            )
        super().__init__()
        self.recorder = recorder
        self._pending: dict[UUID, dict[str, Any]] = {}

    def on_tool_start(
        self,
        serialized: dict[str, Any],
        input_str: str,
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> None:
        self._pending[run_id] = {
            "tool": serialized.get("name", "unknown"),
            "input": {"input": input_str},
            "start": datetime.now(timezone.utc),
        }

    def on_tool_end(
        self,
        output: str,
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> None:
        pending = self._pending.pop(run_id, None)
        if pending is None:
            return
        elapsed = int(
            (datetime.now(timezone.utc) - pending["start"]).total_seconds() * 1000
        )
        self.recorder.record(
            tool=pending["tool"],
            input=pending["input"],
            output={"output": output},
            duration_ms=elapsed,
        )

    def on_tool_error(
        self,
        error: BaseException,
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> None:
        pending = self._pending.pop(run_id, None)
        if pending is None:
            return
        elapsed = int(
            (datetime.now(timezone.utc) - pending["start"]).total_seconds() * 1000
        )
        self.recorder.record(
            tool=pending["tool"],
            input=pending["input"],
            output={"error": str(error)},
            duration_ms=elapsed,
        )
