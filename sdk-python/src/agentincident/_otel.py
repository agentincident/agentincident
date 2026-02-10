"""Optional OpenTelemetry span exporter for AgentIncident trace entries."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, Sequence

if TYPE_CHECKING:
    from .types import TraceEntry

try:
    from opentelemetry import trace as otel_trace
    from opentelemetry.sdk.trace.export import SpanExportResult

    _HAS_OTEL = True
except ImportError:
    _HAS_OTEL = False


def _check_otel() -> None:
    if not _HAS_OTEL:
        raise ImportError(
            "OpenTelemetry is required. Install with: pip install agentincident[otel]"
        )


class AgentIncidentSpanExporter:
    """Export AgentIncident trace entries as OTel spans.

    Usage:
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import SimpleSpanProcessor
        from agentincident._otel import AgentIncidentSpanExporter

        exporter = AgentIncidentSpanExporter()
        provider = TracerProvider()
        provider.add_span_processor(SimpleSpanProcessor(exporter))
    """

    def __init__(self) -> None:
        _check_otel()
        self._spans: list[dict[str, Any]] = []

    def export(self, spans: Sequence[Any]) -> Any:
        """Export OTel spans, storing them internally."""
        for span in spans:
            self._spans.append({
                "name": span.name,
                "start_time": span.start_time,
                "end_time": span.end_time,
                "attributes": dict(span.attributes) if span.attributes else {},
            })
        return SpanExportResult.SUCCESS if _HAS_OTEL else None

    def shutdown(self) -> None:
        pass

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        return True

    @property
    def exported_spans(self) -> list[dict[str, Any]]:
        return list(self._spans)


def trace_entries_to_spans(
    entries: list[TraceEntry],
    tracer_name: str = "agentincident",
) -> None:
    """Create OTel spans from AgentIncident trace entries.

    Requires an active OTel TracerProvider to be configured.
    """
    _check_otel()
    tracer = otel_trace.get_tracer(tracer_name)
    for entry in entries:
        with tracer.start_as_current_span(entry.tool) as span:
            span.set_attribute("agentincident.seq", entry.seq)
            span.set_attribute("agentincident.hash", entry.hash)
            span.set_attribute("agentincident.irreversible", entry.irreversible)
            if entry.duration_ms is not None:
                span.set_attribute("agentincident.duration_ms", entry.duration_ms)
            if entry.agent_reasoning is not None:
                span.set_attribute("agentincident.agent_reasoning", entry.agent_reasoning)
