"""Tests for schema validation."""
from __future__ import annotations

import pytest

from agentincident import (
    Constraint,
    Incident,
    Meta,
    TraceEntry,
    compute_hash,
    get_schema,
    incident_to_dict,
    validate,
)
from datetime import datetime, timezone


class TestGetSchema:
    def test_returns_dict(self):
        schema = get_schema()
        assert isinstance(schema, dict)

    def test_has_required_keys(self):
        schema = get_schema()
        assert "$schema" in schema
        assert "properties" in schema
        assert "required" in schema

    def test_schema_is_cached(self):
        s1 = get_schema()
        s2 = get_schema()
        assert s1 is s2


class TestValidateMinimalRecord:
    def test_valid_minimal(self, minimal_incident):
        d = incident_to_dict(minimal_incident)
        errors = validate(d, level="core")
        assert errors == []

    def test_valid_incident_object(self, minimal_incident):
        errors = validate(minimal_incident, level="core")
        assert errors == []


class TestValidateInvalid:
    def test_missing_trace(self):
        data = {
            "constraints": [{"policy": "p", "eval_result": "pass"}],
            "fault_class": "UNKNOWN",
            "impact_score": 1,
            "loss_amount_usd": None,
        }
        errors = validate(data, level="core")
        assert len(errors) > 0

    def test_missing_constraints(self):
        data = {
            "trace": [
                {
                    "seq": 1,
                    "tool": "t",
                    "input": {},
                    "output": {},
                    "ts": "2026-01-01T00:00:00Z",
                    "hash": "sha256:abc",
                }
            ],
            "fault_class": "UNKNOWN",
            "impact_score": 1,
            "loss_amount_usd": None,
        }
        errors = validate(data, level="core")
        assert len(errors) > 0

    def test_invalid_fault_class(self):
        data = {
            "trace": [
                {
                    "seq": 1,
                    "tool": "t",
                    "input": {},
                    "output": {},
                    "ts": "2026-01-01T00:00:00Z",
                    "hash": "sha256:abc",
                }
            ],
            "constraints": [{"policy": "p", "eval_result": "pass"}],
            "fault_class": "INVALID_CLASS",
            "impact_score": 1,
            "loss_amount_usd": None,
        }
        errors = validate(data, level="core")
        assert len(errors) > 0

    def test_impact_score_out_of_range(self):
        data = {
            "trace": [
                {
                    "seq": 1,
                    "tool": "t",
                    "input": {},
                    "output": {},
                    "ts": "2026-01-01T00:00:00Z",
                    "hash": "sha256:abc",
                }
            ],
            "constraints": [{"policy": "p", "eval_result": "pass"}],
            "fault_class": "UNKNOWN",
            "impact_score": 10,
            "loss_amount_usd": None,
        }
        errors = validate(data, level="core")
        assert len(errors) > 0

    def test_empty_trace(self):
        data = {
            "trace": [],
            "constraints": [{"policy": "p", "eval_result": "pass"}],
            "fault_class": "UNKNOWN",
            "impact_score": 1,
            "loss_amount_usd": None,
        }
        errors = validate(data, level="core")
        assert len(errors) > 0

    def test_empty_constraints(self):
        data = {
            "trace": [
                {
                    "seq": 1,
                    "tool": "t",
                    "input": {},
                    "output": {},
                    "ts": "2026-01-01T00:00:00Z",
                    "hash": "sha256:abc",
                }
            ],
            "constraints": [],
            "fault_class": "UNKNOWN",
            "impact_score": 1,
            "loss_amount_usd": None,
        }
        errors = validate(data, level="core")
        assert len(errors) > 0


class TestValidateLevels:
    def _make_standard_data(self):
        return {
            "trace": [
                {
                    "seq": 1,
                    "tool": "t",
                    "input": {},
                    "output": {},
                    "ts": "2026-01-01T00:00:00Z",
                    "hash": "sha256:abc",
                }
            ],
            "constraints": [{"policy": "p", "eval_result": "pass"}],
            "fault_class": "UNKNOWN",
            "impact_score": 1,
            "loss_amount_usd": None,
            "meta": {"schema": "agentincident/v0.1"},
            "classification": {"fault_class": "UNKNOWN"},
            "loss_estimate": {"total_usd": 100},
        }

    def test_standard_valid(self):
        data = self._make_standard_data()
        errors = validate(data, level="standard")
        assert errors == []

    def test_standard_missing_meta(self):
        data = self._make_standard_data()
        del data["meta"]
        errors = validate(data, level="standard")
        assert len(errors) > 0

    def test_unknown_level(self):
        errors = validate({}, level="bogus")
        assert len(errors) > 0
        assert "Unknown" in errors[0]
