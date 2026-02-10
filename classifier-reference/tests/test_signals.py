"""Tests for signal extraction functions."""

from agentincident_classifier.signals import (
    extract_constraint_signals,
    extract_error_signals,
    extract_irreversible_actions,
    extract_timing_anomalies,
)


class TestExtractErrorSignals:
    def test_error_key_in_output(self):
        trace = [
            {"seq": 1, "tool": "api.call", "output": {"error": "not found"}},
        ]
        signals = extract_error_signals(trace)
        assert len(signals) == 1
        assert signals[0]["error_type"] == "error_key"
        assert signals[0]["tool"] == "api.call"

    def test_exception_key_in_output(self):
        trace = [
            {"seq": 1, "tool": "db.query", "output": {"exception": "connection refused"}},
        ]
        signals = extract_error_signals(trace)
        assert len(signals) == 1
        assert signals[0]["error_type"] == "error_key"

    def test_http_error_status(self):
        trace = [
            {"seq": 1, "tool": "api.call", "output": {"status": 502, "body": "bad gateway"}},
        ]
        signals = extract_error_signals(trace)
        assert len(signals) == 1
        assert signals[0]["error_type"] == "http_error"

    def test_string_status_failed(self):
        trace = [
            {"seq": 1, "tool": "task.run", "output": {"status": "failed"}},
        ]
        signals = extract_error_signals(trace)
        assert len(signals) == 1
        assert signals[0]["error_type"] == "status_error"

    def test_no_errors(self):
        trace = [
            {"seq": 1, "tool": "api.call", "output": {"status": 200, "data": "ok"}},
        ]
        signals = extract_error_signals(trace)
        assert len(signals) == 0

    def test_empty_trace(self):
        assert extract_error_signals([]) == []


class TestExtractConstraintSignals:
    def test_all_pass(self):
        constraints = [
            {"policy": "p1", "eval_result": "pass"},
            {"policy": "p2", "eval_result": "pass"},
        ]
        result = extract_constraint_signals(constraints)
        assert result["total"] == 2
        assert result["passed"] == 2
        assert result["failed"] == 0
        assert result["failed_policies"] == []

    def test_with_failures(self):
        constraints = [
            {"policy": "p1", "eval_result": "pass"},
            {"policy": "p2", "eval_result": "fail"},
        ]
        result = extract_constraint_signals(constraints)
        assert result["failed"] == 1
        assert result["failed_policies"] == ["p2"]

    def test_with_gaps(self):
        constraints = [
            {"policy": "p1", "eval_result": "pass", "gaps_identified": ["missing X"]},
        ]
        result = extract_constraint_signals(constraints)
        assert result["has_gaps"] is True
        assert "missing X" in result["gaps"]

    def test_no_gaps(self):
        constraints = [
            {"policy": "p1", "eval_result": "pass"},
        ]
        result = extract_constraint_signals(constraints)
        assert result["has_gaps"] is False


class TestExtractIrreversibleActions:
    def test_finds_irreversible(self):
        trace = [
            {"seq": 1, "tool": "read", "irreversible": False},
            {"seq": 2, "tool": "transfer", "irreversible": True, "ts": "2026-01-01T00:00:00Z"},
        ]
        result = extract_irreversible_actions(trace)
        assert len(result) == 1
        assert result[0]["tool"] == "transfer"

    def test_none_irreversible(self):
        trace = [
            {"seq": 1, "tool": "read"},
        ]
        assert extract_irreversible_actions(trace) == []


class TestExtractTimingAnomalies:
    def test_high_duration(self):
        trace = [
            {"seq": 1, "tool": "slow.api", "duration_ms": 45000, "output": {}},
        ]
        result = extract_timing_anomalies(trace)
        assert len(result) == 1
        assert result[0]["reason"] == "high_duration"

    def test_timeout_in_output(self):
        trace = [
            {"seq": 1, "tool": "api.call", "duration_ms": 5000, "output": {"error": "request timed out"}},
        ]
        result = extract_timing_anomalies(trace)
        assert len(result) == 1
        assert result[0]["reason"] == "timeout_in_output"

    def test_normal_duration(self):
        trace = [
            {"seq": 1, "tool": "fast.api", "duration_ms": 100, "output": {"ok": True}},
        ]
        assert extract_timing_anomalies(trace) == []
