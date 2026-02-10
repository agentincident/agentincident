"""Tests for AgentIncident types (dataclasses)."""
from __future__ import annotations

from datetime import datetime, timezone

from agentincident import (
    Classification,
    Constraint,
    ConstraintUpdate,
    Incident,
    Liability,
    LossEstimate,
    Meta,
    Response,
    ResponseAction,
    TraceEntry,
    Verification,
)


class TestTraceEntry:
    def test_construction(self):
        entry = TraceEntry(
            seq=1,
            tool="test.tool",
            input={"key": "value"},
            output={"result": "ok"},
            ts=datetime(2026, 1, 1, tzinfo=timezone.utc),
            hash="sha256:abc123",
        )
        assert entry.seq == 1
        assert entry.tool == "test.tool"
        assert entry.hash == "sha256:abc123"

    def test_defaults(self):
        entry = TraceEntry(
            seq=1,
            tool="t",
            input={},
            output={},
            ts=datetime.now(timezone.utc),
            hash="sha256:x",
        )
        assert entry.duration_ms is None
        assert entry.irreversible is False
        assert entry.agent_reasoning is None

    def test_slots(self):
        assert hasattr(TraceEntry, "__slots__")


class TestConstraint:
    def test_construction(self):
        c = Constraint(policy="pol", eval_result="pass")
        assert c.policy == "pol"
        assert c.eval_result == "pass"

    def test_defaults(self):
        c = Constraint(policy="p", eval_result="fail")
        assert c.version is None
        assert c.breach_delta is None
        assert c.gaps_identified == []

    def test_slots(self):
        assert hasattr(Constraint, "__slots__")


class TestMeta:
    def test_defaults(self):
        m = Meta()
        assert m.schema == "agentincident/v0.1"
        assert m.incident_type == "INCIDENT"
        assert m.incident_id is None
        assert m.agent is None

    def test_slots(self):
        assert hasattr(Meta, "__slots__")


class TestClassification:
    def test_construction(self):
        c = Classification(fault_class="AGENT_ERROR")
        assert c.fault_class == "AGENT_ERROR"
        assert c.status == "draft"

    def test_defaults(self):
        c = Classification(fault_class="UNKNOWN")
        assert c.evidence == []
        assert c.counterfactuals == []
        assert c.revision_history == []
        assert c.confidence is None

    def test_slots(self):
        assert hasattr(Classification, "__slots__")


class TestLiability:
    def test_construction(self):
        l = Liability(primary="spec_owner:team@acme.com")
        assert l.primary == "spec_owner:team@acme.com"
        assert l.contributing == []
        assert l.policy_owner is None

    def test_slots(self):
        assert hasattr(Liability, "__slots__")


class TestLossEstimate:
    def test_construction(self):
        le = LossEstimate(total_usd=50000)
        assert le.total_usd == 50000
        assert le.confidence == "medium"
        assert le.breakdown == {}

    def test_slots(self):
        assert hasattr(LossEstimate, "__slots__")


class TestResponseAction:
    def test_construction(self):
        ra = ResponseAction(description="Fix it", status="done")
        assert ra.description == "Fix it"
        assert ra.owner is None
        assert ra.completed_at is None

    def test_slots(self):
        assert hasattr(ResponseAction, "__slots__")


class TestVerification:
    def test_construction(self):
        v = Verification(test="replay", method="deterministic", result="pass")
        assert v.test == "replay"

    def test_slots(self):
        assert hasattr(Verification, "__slots__")


class TestConstraintUpdate:
    def test_construction(self):
        cu = ConstraintUpdate(from_policy="v3", to_policy="v4")
        assert cu.from_policy == "v3"
        assert cu.to_policy == "v4"
        assert cu.diff is None
        assert cu.deployed_at is None

    def test_slots(self):
        assert hasattr(ConstraintUpdate, "__slots__")


class TestResponse:
    def test_defaults(self):
        r = Response()
        assert r.actions == []
        assert r.constraint_update is None
        assert r.verification == []
        assert r.time_to_detect_sec is None

    def test_slots(self):
        assert hasattr(Response, "__slots__")


class TestIncident:
    def test_construction(self, sample_trace_entry, sample_constraint):
        inc = Incident(
            trace=[sample_trace_entry],
            constraints=[sample_constraint],
            fault_class="AGENT_ERROR",
            impact_score=3,
            loss_amount_usd=1000.0,
        )
        assert inc.fault_class == "AGENT_ERROR"
        assert inc.impact_score == 3
        assert len(inc.trace) == 1
        assert len(inc.constraints) == 1

    def test_defaults(self, sample_trace_entry, sample_constraint):
        inc = Incident(
            trace=[sample_trace_entry],
            constraints=[sample_constraint],
            fault_class="UNKNOWN",
            impact_score=1,
            loss_amount_usd=None,
        )
        assert inc.meta is None
        assert inc.classification is None
        assert inc.liability is None
        assert inc.loss_estimate is None
        assert inc.response is None
        assert inc.loss_amount_usd is None

    def test_slots(self):
        assert hasattr(Incident, "__slots__")
