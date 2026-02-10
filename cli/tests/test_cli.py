"""Tests for CLI main entry point."""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest


MINIMAL_INCIDENT = {
    "trace": [
        {
            "seq": 1,
            "tool": "stripe.refund",
            "input": {"charge": "ch_9xK", "amount": 47218},
            "output": {"refund_id": "re_Xp7", "status": "succeeded"},
            "ts": "2026-02-09T22:41:07Z",
            "hash": "sha256:e1d4f60a2",
        }
    ],
    "constraints": [
        {"policy": "refund_policy_v3", "eval_result": "pass"}
    ],
    "fault_class": "SPEC_AMBIGUITY",
    "impact_score": 4,
    "loss_amount_usd": 47218.00,
}


@pytest.fixture
def incident_file(tmp_path):
    path = tmp_path / "incident.json"
    path.write_text(json.dumps(MINIMAL_INCIDENT))
    return str(path)


class TestCLIReport:
    def test_report_to_stdout(self, incident_file):
        result = subprocess.run(
            [sys.executable, "-m", "agentincident_cli.main", "report", incident_file],
            capture_output=True, text=True,
        )
        assert result.returncode == 0
        assert "Agent Incident Report" in result.stdout
        assert "SPEC_AMBIGUITY" in result.stdout

    def test_report_to_file(self, incident_file, tmp_path):
        out_file = str(tmp_path / "report.md")
        result = subprocess.run(
            [sys.executable, "-m", "agentincident_cli.main", "report", incident_file, "--output", out_file],
            capture_output=True, text=True,
        )
        assert result.returncode == 0
        content = Path(out_file).read_text()
        assert "Agent Incident Report" in content

    def test_report_nonexistent_file(self):
        result = subprocess.run(
            [sys.executable, "-m", "agentincident_cli.main", "report", "/nonexistent.json"],
            capture_output=True, text=True,
        )
        assert result.returncode != 0

    def test_report_invalid_json(self, tmp_path):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text("not json")
        result = subprocess.run(
            [sys.executable, "-m", "agentincident_cli.main", "report", str(bad_file)],
            capture_output=True, text=True,
        )
        assert result.returncode != 0


class TestCLIValidate:
    def test_validate_valid(self, incident_file):
        result = subprocess.run(
            [sys.executable, "-m", "agentincident_cli.main", "validate", incident_file],
            capture_output=True, text=True,
        )
        assert result.returncode == 0
        assert "OK" in result.stdout

    def test_validate_with_level(self, incident_file):
        result = subprocess.run(
            [sys.executable, "-m", "agentincident_cli.main", "validate", incident_file, "--level", "core"],
            capture_output=True, text=True,
        )
        assert result.returncode == 0


class TestCLISchema:
    def test_schema_output(self):
        result = subprocess.run(
            [sys.executable, "-m", "agentincident_cli.main", "schema"],
            capture_output=True, text=True,
        )
        assert result.returncode == 0
        schema = json.loads(result.stdout)
        assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert "AgentIncident" in schema["title"]
