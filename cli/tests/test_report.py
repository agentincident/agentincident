"""Tests for report generation."""

from agentincident_cli.report import generate_report, _one_line_summary


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


FULL_INCIDENT = {
    "meta": {
        "schema": "agentincident/v0.1",
        "incident_id": "INC-2026-0247",
        "incident_type": "INCIDENT",
        "created_at": "2026-02-10T03:17:42Z",
        "agent": "refund-processor-v3",
        "environment": "production",
    },
    "trace": [
        {
            "seq": 1,
            "tool": "stripe.charges.list",
            "input": {"customer": "cus_4491", "limit": 10},
            "output": {"charges": ["ch_9xK", "ch_A2m"]},
            "ts": "2026-02-09T22:41:04.112Z",
            "hash": "sha256:a3f8c1d7e",
        },
        {
            "seq": 2,
            "tool": "stripe.refund",
            "input": {"charge": "ch_9xK", "amount": 47218},
            "output": {"refund_id": "re_Xp7", "status": "succeeded"},
            "ts": "2026-02-09T22:41:07.331Z",
            "hash": "sha256:e1d4f60a2",
        },
    ],
    "constraints": [
        {
            "policy": "refund_policy_v3",
            "version": "3.1.0",
            "eval_result": "pass",
            "gaps_identified": ["no cumulative_exposure constraint"],
        }
    ],
    "fault_class": "SPEC_AMBIGUITY",
    "impact_score": 4,
    "loss_amount_usd": None,
    "classification": {
        "fault_class": "SPEC_AMBIGUITY",
        "confidence": 0.84,
        "classifier": "hybrid",
        "status": "human_confirmed",
    },
    "loss_estimate": {
        "total_usd": 48868,
        "confidence": "medium",
        "breakdown": {
            "direct_cash_loss": 47218,
            "remediation_labor": 1200,
            "fees": 450,
        },
    },
}


class TestGenerateReport:
    def test_minimal_report_contains_required_sections(self):
        report = generate_report(MINIMAL_INCIDENT)
        assert "# Agent Incident Report" in report
        assert "## 1. Executive Summary" in report
        assert "## 2. Timeline" in report
        assert "## 3. Fault Classification" in report
        assert "## 4. Impact Assessment" in report
        assert "agentincident.com" in report

    def test_minimal_report_shows_fault_class(self):
        report = generate_report(MINIMAL_INCIDENT)
        assert "SPEC_AMBIGUITY" in report

    def test_minimal_report_shows_impact_score(self):
        report = generate_report(MINIMAL_INCIDENT)
        assert "4 / 5" in report or "4/5" in report
        assert "High" in report

    def test_minimal_report_shows_loss(self):
        report = generate_report(MINIMAL_INCIDENT)
        assert "$47,218.00" in report

    def test_full_report_shows_incident_id(self):
        report = generate_report(FULL_INCIDENT)
        assert "INC-2026-0247" in report

    def test_full_report_shows_agent(self):
        report = generate_report(FULL_INCIDENT)
        assert "refund-processor-v3" in report

    def test_full_report_shows_classification_details(self):
        report = generate_report(FULL_INCIDENT)
        assert "0.84" in report
        assert "hybrid" in report

    def test_full_report_shows_loss_breakdown(self):
        report = generate_report(FULL_INCIDENT)
        assert "direct_cash_loss" in report
        assert "$47,218.00" in report
        assert "$48,868.00" in report

    def test_full_report_shows_estimated_loss(self):
        report = generate_report(FULL_INCIDENT)
        assert "Estimated loss: $48,868.00" in report

    def test_report_with_unidentified(self):
        incident = dict(MINIMAL_INCIDENT)
        report = generate_report(incident)
        assert "Unidentified" in report

    def test_auto_classification_note(self):
        incident = dict(MINIMAL_INCIDENT)
        incident["fault_class"] = "UNKNOWN"
        report = generate_report(incident)
        # If classifier is installed, should show auto-classify note
        # If not installed, should stay UNKNOWN
        assert "UNKNOWN" in report or "automatically classified" in report

    def test_timeline_rows(self):
        report = generate_report(FULL_INCIDENT)
        assert "`stripe.charges.list`" in report
        assert "`stripe.refund`" in report

    def test_footer_has_both_links(self):
        report = generate_report(MINIMAL_INCIDENT)
        assert "github.com/agentincident/agentincident" in report
        assert "agentincident.com" in report


class TestOneLineSummary:
    def test_basic_summary(self):
        entry = {
            "input": {"customer": "cus_4491", "limit": 10},
            "output": {"charges": ["ch_9xK", "ch_A2m"]},
        }
        summary = _one_line_summary(entry)
        assert "customer=" in summary
        assert "->" in summary

    def test_empty_entry(self):
        entry = {"input": {}, "output": {}}
        summary = _one_line_summary(entry)
        assert summary == "—"

    def test_truncation(self):
        entry = {
            "input": {"very_long_key": "a" * 200},
            "output": {},
        }
        summary = _one_line_summary(entry, max_len=50)
        assert len(summary) <= 50
        assert summary.endswith("...")
