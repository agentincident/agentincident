"""Tests for schema validation command."""

import json
import os
import tempfile

import pytest

from agentincident_cli.validate_cmd import validate_file


MINIMAL_VALID = {
    "trace": [
        {
            "seq": 1,
            "tool": "test.tool",
            "input": {"key": "value"},
            "output": {"result": "ok"},
            "ts": "2026-01-01T00:00:00Z",
            "hash": "sha256:abc123def456",
        }
    ],
    "constraints": [
        {"policy": "test_policy", "eval_result": "pass"}
    ],
    "fault_class": "UNKNOWN",
    "impact_score": 3,
    "loss_amount_usd": None,
}


@pytest.fixture
def valid_json_file(tmp_path):
    path = tmp_path / "valid.json"
    path.write_text(json.dumps(MINIMAL_VALID))
    return str(path)


@pytest.fixture
def invalid_json_file(tmp_path):
    path = tmp_path / "invalid.json"
    path.write_text("not json")
    return str(path)


@pytest.fixture
def invalid_incident_file(tmp_path):
    path = tmp_path / "bad_incident.json"
    # Missing required fields
    path.write_text(json.dumps({"trace": []}))
    return str(path)


class TestValidateFile:
    def test_valid_file(self, valid_json_file):
        is_valid, errors = validate_file(valid_json_file)
        assert is_valid
        assert errors == []

    def test_invalid_json(self, invalid_json_file):
        is_valid, errors = validate_file(invalid_json_file)
        assert not is_valid
        assert any("Invalid JSON" in e for e in errors)

    def test_file_not_found(self):
        is_valid, errors = validate_file("/nonexistent/file.json")
        assert not is_valid
        assert any("not found" in e for e in errors)

    def test_invalid_incident(self, invalid_incident_file):
        is_valid, errors = validate_file(invalid_incident_file)
        assert not is_valid
        assert len(errors) > 0
