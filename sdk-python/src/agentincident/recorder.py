from __future__ import annotations

import functools
import json
from datetime import datetime, timezone
from typing import Any, Callable

from .hash import compute_hash
from .schema import validate as schema_validate
from .types import Constraint, Incident, Meta, TraceEntry


class Recorder:
    """Record agent tool calls and build AgentIncident records.

    Supports three modes:
    - Context manager: ``with Recorder() as rec: ...``
    - Decorator: ``@rec.trace``
    - Manual: ``rec.record(tool, input, output)``
    """

    def __init__(
        self,
        agent: str | None = None,
        framework: str | None = None,
        environment: str | None = None,
        trigger: str | None = None,
    ) -> None:
        self._entries: list[TraceEntry] = []
        self._seq = 0
        self._agent = agent
        self._framework = framework
        self._environment = environment
        self._trigger = trigger
        self._started_at: datetime | None = None

    def __enter__(self) -> Recorder:
        self._started_at = datetime.now(timezone.utc)
        return self

    def __exit__(self, *exc: Any) -> None:
        pass

    @property
    def entries(self) -> list[TraceEntry]:
        return list(self._entries)

    def record(
        self,
        tool: str,
        input: dict[str, Any],
        output: dict[str, Any],
        irreversible: bool = False,
        agent_reasoning: str | None = None,
        duration_ms: int | None = None,
    ) -> TraceEntry:
        """Record a tool call. Auto-computes seq, ts, and hash."""
        self._seq += 1
        entry = TraceEntry(
            seq=self._seq,
            tool=tool,
            input=input,
            output=output,
            ts=datetime.now(timezone.utc),
            hash=compute_hash(input, output),
            duration_ms=duration_ms,
            irreversible=irreversible,
            agent_reasoning=agent_reasoning,
        )
        self._entries.append(entry)
        return entry

    def trace(
        self,
        func: Callable[..., Any] | None = None,
        *,
        tool: str | None = None,
        irreversible: bool = False,
    ) -> Any:
        """Decorator that wraps a function call as a trace entry.

        Usage:
            @rec.trace
            def my_tool(x, y): ...

            @rec.trace(tool="custom_name", irreversible=True)
            def my_tool(x, y): ...
        """
        def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
            @functools.wraps(fn)
            def wrapper(*args: Any, **kwargs: Any) -> Any:
                tool_name = tool or fn.__name__
                input_data = kwargs if kwargs else {"args": list(args)} if args else {}
                start = datetime.now(timezone.utc)
                try:
                    result = fn(*args, **kwargs)
                except Exception as exc:
                    elapsed = int(
                        (datetime.now(timezone.utc) - start).total_seconds() * 1000
                    )
                    self.record(
                        tool=tool_name,
                        input=input_data,
                        output={"error": str(exc)},
                        irreversible=irreversible,
                        duration_ms=elapsed,
                    )
                    raise
                elapsed = int(
                    (datetime.now(timezone.utc) - start).total_seconds() * 1000
                )
                output_data = (
                    result if isinstance(result, dict) else {"result": result}
                )
                self.record(
                    tool=tool_name,
                    input=input_data,
                    output=output_data,
                    irreversible=irreversible,
                    duration_ms=elapsed,
                )
                return result
            return wrapper

        if func is not None:
            return decorator(func)
        return decorator

    def to_incident(
        self,
        fault_class: str,
        impact_score: int,
        loss_amount_usd: float | None,
        constraints: list[Constraint],
        **kwargs: Any,
    ) -> Incident:
        """Build an Incident from the recorded trace and metadata."""
        now = datetime.now(timezone.utc)
        meta = Meta(
            schema="agentincident/v0.1",
            created_at=self._started_at or now,
            updated_at=now,
            agent=self._agent,
            framework=self._framework,
            environment=self._environment,
            trigger=self._trigger,
        )
        return Incident(
            trace=list(self._entries),
            constraints=constraints,
            fault_class=fault_class,
            impact_score=impact_score,
            loss_amount_usd=loss_amount_usd,
            meta=meta,
            **kwargs,
        )

    def to_dict(self) -> dict[str, Any]:
        """Export recorded entries as a dict (trace only, no incident wrapper)."""
        from .export import _trace_entry_to_dict
        return {"trace": [_trace_entry_to_dict(e) for e in self._entries]}

    def to_json(self, indent: int = 2) -> str:
        """Export recorded entries as JSON."""
        return json.dumps(self.to_dict(), indent=indent, default=str)

    def validate(self, level: str = "core") -> list[str]:
        """Validate the current state. Requires a full incident for meaningful validation."""
        return schema_validate(self.to_dict(), level=level)
