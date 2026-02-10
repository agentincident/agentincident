"""Tests for the Recorder class."""
from __future__ import annotations

import time
from datetime import datetime, timezone

from agentincident import Constraint, Recorder


class TestRecorderContextManager:
    def test_basic_recording(self):
        with Recorder() as rec:
            entry = rec.record(
                tool="test.tool",
                input={"key": "value"},
                output={"result": "ok"},
            )
        assert entry.seq == 1
        assert entry.tool == "test.tool"
        assert entry.hash.startswith("sha256:")
        assert isinstance(entry.ts, datetime)

    def test_auto_seq(self):
        with Recorder() as rec:
            e1 = rec.record(tool="a", input={}, output={})
            e2 = rec.record(tool="b", input={}, output={})
            e3 = rec.record(tool="c", input={}, output={})
        assert e1.seq == 1
        assert e2.seq == 2
        assert e3.seq == 3

    def test_auto_hash(self):
        with Recorder() as rec:
            entry = rec.record(
                tool="t",
                input={"x": 1},
                output={"y": 2},
            )
        assert entry.hash.startswith("sha256:")
        assert len(entry.hash) == 7 + 64  # "sha256:" + 64 hex chars

    def test_auto_ts(self):
        before = datetime.now(timezone.utc)
        with Recorder() as rec:
            entry = rec.record(tool="t", input={}, output={})
        after = datetime.now(timezone.utc)
        assert before <= entry.ts <= after

    def test_entries_property(self):
        with Recorder() as rec:
            rec.record(tool="a", input={}, output={})
            rec.record(tool="b", input={}, output={})
        entries = rec.entries
        assert len(entries) == 2
        # Ensure it's a copy
        entries.clear()
        assert len(rec.entries) == 2

    def test_metadata(self):
        with Recorder(agent="bot", framework="test", environment="dev") as rec:
            rec.record(tool="t", input={}, output={})
            incident = rec.to_incident(
                fault_class="UNKNOWN",
                impact_score=1,
                loss_amount_usd=None,
                constraints=[Constraint(policy="p", eval_result="pass")],
            )
        assert incident.meta is not None
        assert incident.meta.agent == "bot"
        assert incident.meta.framework == "test"
        assert incident.meta.environment == "dev"


class TestRecorderDecorator:
    def test_basic_decorator(self):
        rec = Recorder()

        @rec.trace
        def my_tool(x, y):
            return {"sum": x + y}

        result = my_tool(x=1, y=2)
        assert result == {"sum": 3}
        assert len(rec.entries) == 1
        assert rec.entries[0].tool == "my_tool"
        assert rec.entries[0].output == {"sum": 3}

    def test_decorator_with_options(self):
        rec = Recorder()

        @rec.trace(tool="custom.name", irreversible=True)
        def do_thing():
            return {"done": True}

        do_thing()
        assert rec.entries[0].tool == "custom.name"
        assert rec.entries[0].irreversible is True

    def test_decorator_captures_error(self):
        rec = Recorder()

        @rec.trace
        def failing_tool():
            raise ValueError("boom")

        try:
            failing_tool()
        except ValueError:
            pass

        assert len(rec.entries) == 1
        assert "boom" in rec.entries[0].output["error"]

    def test_decorator_duration(self):
        rec = Recorder()

        @rec.trace
        def slow_tool():
            time.sleep(0.05)
            return {"ok": True}

        slow_tool()
        assert rec.entries[0].duration_ms is not None
        assert rec.entries[0].duration_ms >= 40  # at least ~50ms

    def test_decorator_non_dict_return(self):
        rec = Recorder()

        @rec.trace
        def simple():
            return 42

        result = simple()
        assert result == 42
        assert rec.entries[0].output == {"result": 42}


class TestRecorderToIncident:
    def test_to_incident(self):
        with Recorder(agent="test-agent") as rec:
            rec.record(tool="t", input={"a": 1}, output={"b": 2})
            incident = rec.to_incident(
                fault_class="AGENT_ERROR",
                impact_score=3,
                loss_amount_usd=1000,
                constraints=[Constraint(policy="pol", eval_result="fail")],
            )
        assert incident.fault_class == "AGENT_ERROR"
        assert incident.impact_score == 3
        assert incident.loss_amount_usd == 1000
        assert len(incident.trace) == 1
        assert len(incident.constraints) == 1
        assert incident.meta is not None
        assert incident.meta.agent == "test-agent"

    def test_to_dict(self):
        rec = Recorder()
        rec.record(tool="t", input={}, output={})
        d = rec.to_dict()
        assert "trace" in d
        assert len(d["trace"]) == 1

    def test_to_json(self):
        rec = Recorder()
        rec.record(tool="t", input={}, output={})
        j = rec.to_json()
        assert '"trace"' in j
        assert '"tool"' in j


class TestRecorderDurationTracking:
    def test_manual_duration(self):
        rec = Recorder()
        entry = rec.record(
            tool="t", input={}, output={}, duration_ms=500
        )
        assert entry.duration_ms == 500

    def test_irreversible_flag(self):
        rec = Recorder()
        entry = rec.record(
            tool="t", input={}, output={}, irreversible=True
        )
        assert entry.irreversible is True

    def test_agent_reasoning(self):
        rec = Recorder()
        entry = rec.record(
            tool="t",
            input={},
            output={},
            agent_reasoning="I chose this because...",
        )
        assert entry.agent_reasoning == "I chose this because..."
