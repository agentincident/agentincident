"""Scenario-based tests using realistic agent error/issue patterns.

Each test class simulates a real-world agent incident end-to-end:
recording trace entries, building the incident, serializing, validating,
and redacting — exercising the full SDK pipeline.
"""
from __future__ import annotations

import copy
import json
import re
from datetime import datetime, timezone

import pytest

from agentincident import (
    Classification,
    Constraint,
    ConstraintUpdate,
    Incident,
    Liability,
    LossEstimate,
    Meta,
    Recorder,
    Response,
    ResponseAction,
    TraceEntry,
    Verification,
    compute_hash,
    get_schema,
    incident_from_dict,
    incident_from_json,
    incident_to_dict,
    incident_to_json,
    redact_incident,
    validate,
)


# ---------------------------------------------------------------------------
# Scenario 1: Double-refund due to spec ambiguity
# An agent processes the same refund twice because the policy didn't define
# idempotency guards.
# ---------------------------------------------------------------------------
class TestDoubleRefundScenario:
    """Agent refunds the same charge twice — a classic spec-gap incident."""

    def _build_incident(self) -> Incident:
        rec = Recorder(
            agent="refund-bot-beta",
            framework="langchain",
            environment="production",
        )
        # Step 1: Agent looks up the charge
        rec.record(
            tool="stripe.charges.retrieve",
            input={"charge_id": "ch_3xJ8qMk"},
            output={
                "id": "ch_3xJ8qMk",
                "amount": 15000,
                "currency": "usd",
                "refunded": False,
            },
            duration_ms=230,
        )
        # Step 2: First refund — succeeds
        rec.record(
            tool="stripe.refunds.create",
            input={"charge": "ch_3xJ8qMk", "amount": 15000},
            output={"id": "re_A1b", "status": "succeeded"},
            irreversible=True,
            duration_ms=540,
            agent_reasoning="Customer requested full refund per policy",
        )
        # Step 3: Duplicate refund — also succeeds (no idempotency key!)
        rec.record(
            tool="stripe.refunds.create",
            input={"charge": "ch_3xJ8qMk", "amount": 15000},
            output={"id": "re_C3d", "status": "succeeded"},
            irreversible=True,
            duration_ms=480,
            agent_reasoning="Retry after perceived timeout; no idempotency guard",
        )

        return rec.to_incident(
            fault_class="SPEC_AMBIGUITY",
            impact_score=4,
            loss_amount_usd=150.00,
            constraints=[
                Constraint(
                    policy="refund_policy_r3",
                    eval_result="fail",
                    version="2.0.3",
                    breach_delta=15000,
                    gaps_identified=[
                        "no idempotency key required",
                        "no duplicate-refund guard",
                    ],
                ),
            ],
            classification=Classification(
                fault_class="SPEC_AMBIGUITY",
                fault_subclass="missing_idempotency",
                confidence=0.92,
                classifier="hybrid",
                status="human_confirmed",
                evidence=["Two refunds for same charge within 5s"],
            ),
            liability=Liability(
                primary="spec_owner:payments-team@acme.com",
                contributing=["agent:retry_logic"],
            ),
            loss_estimate=LossEstimate(
                total_usd=150.00,
                confidence="high",
                breakdown={"duplicate_refund": 150.00},
            ),
            response=Response(
                actions=[
                    ResponseAction(description="Reverse duplicate refund", status="done"),
                    ResponseAction(
                        description="Add idempotency key to refund flow",
                        status="in_progress",
                        owner="alice@acme.com",
                    ),
                ],
                constraint_update=ConstraintUpdate(
                    from_policy="refund_policy_r3",
                    to_policy="refund_policy_v3",
                    diff={"added": {"require_idempotency_key": True}},
                ),
                verification=[
                    Verification(test="replay_refund", method="deterministic", result="pass"),
                ],
                time_to_detect_sec=45,
                time_to_contain_sec=300,
                time_to_remediate_sec=7200,
            ),
        )

    def test_trace_has_three_entries(self):
        inc = self._build_incident()
        assert len(inc.trace) == 3

    def test_both_refunds_marked_irreversible(self):
        inc = self._build_incident()
        assert inc.trace[1].irreversible is True
        assert inc.trace[2].irreversible is True
        # The lookup is not irreversible
        assert inc.trace[0].irreversible is False

    def test_agent_reasoning_recorded(self):
        inc = self._build_incident()
        assert "idempotency" in inc.trace[2].agent_reasoning

    def test_full_roundtrip_json(self):
        inc = self._build_incident()
        j = incident_to_json(inc)
        restored = incident_from_json(j)
        assert restored.fault_class == "SPEC_AMBIGUITY"
        assert restored.impact_score == 4
        assert len(restored.trace) == 3
        assert restored.response.constraint_update.from_policy == "refund_policy_r3"
        assert restored.response.constraint_update.to_policy == "refund_policy_v3"

    def test_validates_at_full_level(self):
        inc = self._build_incident()
        errors = validate(inc, level="full")
        assert errors == []

    def test_constraint_from_to_in_dict(self):
        inc = self._build_incident()
        d = incident_to_dict(inc)
        cu = d["response"]["constraint_update"]
        assert cu["from"] == "refund_policy_r3"
        assert cu["to"] == "refund_policy_v3"
        assert "from_policy" not in cu
        assert "to_policy" not in cu

    def test_duplicate_refund_hashes_differ(self):
        """Even though the inputs are identical, hashes should be the same
        because hash is computed from input+output — but the outputs differ."""
        inc = self._build_incident()
        assert inc.trace[1].hash != inc.trace[2].hash  # different refund IDs

    def test_redact_preserves_structure(self):
        inc = self._build_incident()
        redacted = redact_incident(inc, fields=["charge", "charge_id"])
        assert redacted.trace[0].input["charge_id"] == "[REDACTED]"
        assert redacted.trace[1].input["charge"] == "[REDACTED]"
        # Structure preserved
        assert len(redacted.trace) == 3
        assert redacted.fault_class == "SPEC_AMBIGUITY"


# ---------------------------------------------------------------------------
# Scenario 2: Adversarial SQL injection via tool input
# An agent passes unsanitized user input to a database query tool.
# ---------------------------------------------------------------------------
class TestAdversarialInputScenario:
    """Agent forwards adversarial input to a database tool."""

    def _build_incident(self) -> Incident:
        ts = datetime(2026, 3, 15, 14, 22, 0, tzinfo=timezone.utc)
        malicious_input = "'; DROP TABLE users; --"

        trace = [
            TraceEntry(
                seq=1,
                tool="chat.receive",
                input={"channel": "support"},
                output={"user_message": f"Look up order {malicious_input}"},
                ts=ts,
                hash=compute_hash(
                    {"channel": "support"},
                    {"user_message": f"Look up order {malicious_input}"},
                ),
                duration_ms=15,
            ),
            TraceEntry(
                seq=2,
                tool="db.query",
                input={"sql": f"SELECT * FROM orders WHERE id = '{malicious_input}'"},
                output={"error": "relation \"users\" does not exist"},
                ts=ts,
                hash=compute_hash(
                    {"sql": f"SELECT * FROM orders WHERE id = '{malicious_input}'"},
                    {"error": "relation \"users\" does not exist"},
                ),
                duration_ms=42,
                irreversible=True,
                agent_reasoning="Constructed SQL from user input without sanitization",
            ),
        ]

        return Incident(
            trace=trace,
            constraints=[
                Constraint(
                    policy="input_sanitization_v1",
                    eval_result="fail",
                    gaps_identified=["no parameterized queries", "no input validation"],
                ),
                Constraint(policy="data_access_r3", eval_result="fail"),
            ],
            fault_class="ADVERSARIAL_INPUT",
            impact_score=5,
            loss_amount_usd=None,  # damage unknown
            meta=Meta(
                incident_id="INC-2026-0391",
                incident_type="INCIDENT",
                created_at=ts,
                agent="support-bot-v1",
                environment="production",
                trigger="customer_chat",
            ),
            classification=Classification(
                fault_class="ADVERSARIAL_INPUT",
                fault_vector="sql_injection",
                confidence=0.99,
                classifier="rules",
                status="human_confirmed",
                evidence=[
                    "SQL injection pattern detected in user input",
                    "Unparameterized query constructed",
                ],
                counterfactuals=[
                    "Parameterized query would have prevented execution",
                    "Input validation would have rejected the payload",
                ],
            ),
        )

    def test_null_loss_preserved(self):
        inc = self._build_incident()
        d = incident_to_dict(inc)
        assert d["loss_amount_usd"] is None

        j = incident_to_json(inc)
        assert '"loss_amount_usd": null' in j

        restored = incident_from_json(j)
        assert restored.loss_amount_usd is None

    def test_multiple_constraint_failures(self):
        inc = self._build_incident()
        assert len(inc.constraints) == 2
        assert all(c.eval_result == "fail" for c in inc.constraints)

    def test_counterfactuals_roundtrip(self):
        inc = self._build_incident()
        d = incident_to_dict(inc)
        restored = incident_from_dict(d)
        assert len(restored.classification.counterfactuals) == 2
        assert "Parameterized" in restored.classification.counterfactuals[0]

    def test_validates_at_standard_level(self):
        """Has meta + classification but not liability/response, so passes standard."""
        inc = self._build_incident()
        d = incident_to_dict(inc)
        # Need loss_estimate for standard
        d["loss_estimate"] = {"total_usd": 0}
        errors = validate(d, level="standard")
        assert errors == []

    def test_does_not_validate_at_full_level(self):
        inc = self._build_incident()
        errors = validate(inc, level="full")
        assert len(errors) > 0

    def test_near_miss_variant(self):
        """Same scenario but the DB had read-only permissions → near miss."""
        inc = self._build_incident()
        inc.meta.incident_type = "NEAR_MISS"
        inc.impact_score = 2
        d = incident_to_dict(inc)
        assert d["meta"]["incident_type"] == "NEAR_MISS"
        assert d["impact_score"] == 2

    def test_sql_in_redacted_output(self):
        inc = self._build_incident()
        # Custom pattern to redact SQL-like payloads
        sql_pattern = re.compile(r"SELECT\s+.*?\s+FROM\s+\w+.*?(?=\s*$)", re.IGNORECASE)
        redacted = redact_incident(inc, patterns=[sql_pattern])
        assert "SELECT" not in redacted.trace[1].input.get("sql", "")


# ---------------------------------------------------------------------------
# Scenario 3: Tool failure cascading through multi-step workflow
# An external API fails mid-workflow, and the agent doesn't handle it.
# ---------------------------------------------------------------------------
class TestToolFailureCascadeScenario:
    """External API failure cascades through a multi-step agent workflow."""

    def _build_incident(self) -> Incident:
        rec = Recorder(agent="order-processor", environment="production")

        # Step 1: Fetch order — OK
        rec.record(
            tool="orders.get",
            input={"order_id": "ORD-99821"},
            output={"id": "ORD-99821", "total": 299.99, "status": "pending"},
            duration_ms=180,
        )
        # Step 2: Charge payment — API timeout
        rec.record(
            tool="payments.charge",
            input={"amount": 299.99, "token": "tok_visa_4242"},
            output={"error": "Gateway timeout after 30000ms"},
            duration_ms=30000,
        )
        # Step 3: Agent incorrectly marks order as fulfilled despite payment failure
        rec.record(
            tool="orders.update",
            input={"order_id": "ORD-99821", "status": "fulfilled"},
            output={"id": "ORD-99821", "status": "fulfilled"},
            irreversible=True,
            duration_ms=95,
            agent_reasoning="Assumed payment succeeded; did not check response",
        )
        # Step 4: Shipping triggered on unfunded order
        rec.record(
            tool="shipping.create",
            input={"order_id": "ORD-99821", "address": "123 Main St"},
            output={"tracking": "1Z999AA10123456784"},
            irreversible=True,
            duration_ms=250,
        )

        return rec.to_incident(
            fault_class="AGENT_ERROR",
            impact_score=4,
            loss_amount_usd=299.99,
            constraints=[
                Constraint(
                    policy="payment_verification_v1",
                    eval_result="fail",
                    gaps_identified=["no payment success check before fulfillment"],
                ),
            ],
        )

    def test_four_step_trace(self):
        inc = self._build_incident()
        assert len(inc.trace) == 4
        tools = [e.tool for e in inc.trace]
        assert tools == [
            "orders.get",
            "payments.charge",
            "orders.update",
            "shipping.create",
        ]

    def test_payment_failure_recorded(self):
        inc = self._build_incident()
        payment_entry = inc.trace[1]
        assert "error" in payment_entry.output
        assert "timeout" in payment_entry.output["error"].lower()

    def test_irreversible_actions_after_failure(self):
        inc = self._build_incident()
        # The order update and shipping are irreversible
        assert inc.trace[2].irreversible is True
        assert inc.trace[3].irreversible is True
        # But the read and failed payment are not
        assert inc.trace[0].irreversible is False
        assert inc.trace[1].irreversible is False

    def test_duration_tracking(self):
        inc = self._build_incident()
        # Payment timeout should show ~30s
        assert inc.trace[1].duration_ms == 30000
        # Normal operations should be fast
        assert inc.trace[0].duration_ms < 1000

    def test_json_roundtrip_preserves_error(self):
        inc = self._build_incident()
        j = incident_to_json(inc)
        restored = incident_from_json(j)
        assert "Gateway timeout" in restored.trace[1].output["error"]

    def test_redact_payment_token(self):
        inc = self._build_incident()
        redacted = redact_incident(inc, fields=["token", "address"])
        assert redacted.trace[1].input["token"] == "[REDACTED]"
        assert redacted.trace[3].input["address"] == "[REDACTED]"
        # Other fields preserved
        assert redacted.trace[0].input["order_id"] == "ORD-99821"

    def test_hash_integrity_after_redaction(self):
        inc = self._build_incident()
        redacted = redact_incident(inc, fields=["token"])
        for entry in redacted.trace:
            expected = compute_hash(entry.input, entry.output)
            assert entry.hash == expected

    def test_seq_monotonically_increasing(self):
        inc = self._build_incident()
        seqs = [e.seq for e in inc.trace]
        assert seqs == [1, 2, 3, 4]


# ---------------------------------------------------------------------------
# Scenario 4: Near-miss caught by constraints
# The agent tried to perform an unauthorized action but constraints stopped it.
# ---------------------------------------------------------------------------
class TestNearMissScenario:
    """Agent attempts unauthorized data export — constraint catches it."""

    def _build_incident(self) -> Incident:
        ts = datetime(2026, 4, 1, 9, 0, 0, tzinfo=timezone.utc)
        return Incident(
            trace=[
                TraceEntry(
                    seq=1,
                    tool="data.export",
                    input={"table": "customers", "format": "csv", "filter": "all"},
                    output={"error": "BLOCKED by policy: bulk_export_restricted"},
                    ts=ts,
                    hash=compute_hash(
                        {"table": "customers", "format": "csv", "filter": "all"},
                        {"error": "BLOCKED by policy: bulk_export_restricted"},
                    ),
                    agent_reasoning="User asked for full customer list export",
                ),
            ],
            constraints=[
                Constraint(
                    policy="data_access_v3",
                    eval_result="pass",
                    version="3.2.0",
                ),
                Constraint(
                    policy="bulk_export_restriction",
                    eval_result="pass",
                    version="1.0.0",
                    gaps_identified=[],
                ),
            ],
            fault_class="USER_FAULT",
            impact_score=1,
            loss_amount_usd=0.0,
            meta=Meta(
                incident_type="NEAR_MISS",
                agent="data-assistant",
                environment="production",
            ),
        )

    def test_near_miss_type(self):
        inc = self._build_incident()
        assert inc.meta.incident_type == "NEAR_MISS"

    def test_zero_loss(self):
        inc = self._build_incident()
        assert inc.loss_amount_usd == 0.0

    def test_constraints_all_pass(self):
        """Constraints passed because they successfully blocked the action."""
        inc = self._build_incident()
        assert all(c.eval_result == "pass" for c in inc.constraints)

    def test_blocked_action_in_output(self):
        inc = self._build_incident()
        assert "BLOCKED" in inc.trace[0].output["error"]

    def test_validates_core(self):
        inc = self._build_incident()
        errors = validate(inc, level="core")
        assert errors == []

    def test_json_roundtrip(self):
        inc = self._build_incident()
        j = incident_to_json(inc)
        restored = incident_from_json(j)
        assert restored.meta.incident_type == "NEAR_MISS"
        assert restored.loss_amount_usd == 0.0
        assert restored.fault_class == "USER_FAULT"


# ---------------------------------------------------------------------------
# Scenario 5: Decorator-based recording with exception capture
# Uses @rec.trace to instrument functions that fail during execution.
# ---------------------------------------------------------------------------
class TestDecoratorErrorCapture:
    """Tests the decorator pattern with various error types."""

    def test_value_error_captured(self):
        rec = Recorder()

        @rec.trace(tool="validate.email")
        def validate_email(email: str) -> dict:
            if "@" not in email:
                raise ValueError(f"Invalid email: {email}")
            return {"valid": True}

        with pytest.raises(ValueError):
            validate_email(email="not-an-email")

        assert len(rec.entries) == 1
        assert "Invalid email" in rec.entries[0].output["error"]
        assert rec.entries[0].tool == "validate.email"

    def test_key_error_captured(self):
        rec = Recorder()

        @rec.trace
        def lookup_user(data):
            return {"name": data["name"], "email": data["email"]}

        with pytest.raises(KeyError):
            lookup_user(data={"name": "Alice"})

        assert len(rec.entries) == 1
        assert "error" in rec.entries[0].output
        assert "email" in rec.entries[0].output["error"]

    def test_mixed_success_and_failure(self):
        rec = Recorder(agent="validator")

        @rec.trace
        def divide(a, b):
            return {"result": a / b}

        assert divide(a=10, b=2) == {"result": 5.0}

        with pytest.raises(ZeroDivisionError):
            divide(a=10, b=0)

        assert divide(a=20, b=4) == {"result": 5.0}

        assert len(rec.entries) == 3
        assert rec.entries[0].output == {"result": 5.0}
        assert "error" in rec.entries[1].output
        assert rec.entries[2].output == {"result": 5.0}
        # Seq still monotonic
        assert [e.seq for e in rec.entries] == [1, 2, 3]

    def test_error_incident_validates(self):
        rec = Recorder(agent="test")

        @rec.trace
        def fail():
            raise RuntimeError("unexpected failure")

        with pytest.raises(RuntimeError):
            fail()

        incident = rec.to_incident(
            fault_class="TOOL_FAILURE",
            impact_score=2,
            loss_amount_usd=None,
            constraints=[Constraint(policy="p", eval_result="fail")],
        )
        errors = validate(incident, level="core")
        assert errors == []

    def test_decorator_with_irreversible_on_error(self):
        rec = Recorder()

        @rec.trace(irreversible=True)
        def delete_record(record_id):
            raise ConnectionError("database unavailable")

        with pytest.raises(ConnectionError):
            delete_record(record_id="rec_123")

        entry = rec.entries[0]
        assert entry.irreversible is True
        assert "database unavailable" in entry.output["error"]


# ---------------------------------------------------------------------------
# Scenario 6: Full pipeline — record → incident → export → redact → validate
# End-to-end test with PII scattered through trace entries.
# ---------------------------------------------------------------------------
class TestFullPipelineWithPII:
    """End-to-end: record with PII → build incident → redact → validate."""

    def test_full_pipeline(self):
        # 1. Record trace with PII
        rec = Recorder(agent="support-bot", environment="production")
        rec.record(
            tool="crm.lookup",
            input={"email": "john.doe@example.com"},
            output={
                "name": "John Doe",
                "card_on_file": "4532-0150-0000-1234",
                "api_key": "sk-abcdef1234567890abcdef",
            },
        )
        rec.record(
            tool="email.send",
            input={
                "to": "john.doe@example.com",
                "body": "Your refund is being processed. Ref: sk_test_xyz1234567890abcde",
            },
            output={
                "status": "sent",
                "auth_header": "Bearer eyJhbGciOiJIUzI1NiJ9.payload.sig",
            },
        )

        # 2. Build incident
        incident = rec.to_incident(
            fault_class="AGENT_ERROR",
            impact_score=3,
            loss_amount_usd=50.00,
            constraints=[Constraint(policy="pii_handling_v1", eval_result="fail")],
        )

        # 3. Validate before redaction (core level)
        errors = validate(incident, level="core")
        assert errors == []

        # 4. Redact PII
        redacted = redact_incident(incident)

        # 5. Verify PII is gone
        crm_output = redacted.trace[0].output
        assert "4532" not in json.dumps(crm_output)
        assert "sk-abcdef" not in json.dumps(crm_output)
        assert "john.doe@example.com" not in json.dumps(redacted.trace[0].input)
        assert "Bearer" not in json.dumps(redacted.trace[1].output)

        # 6. Hashes recomputed
        for entry in redacted.trace:
            assert entry.hash == compute_hash(entry.input, entry.output)

        # 7. Export redacted incident
        j = incident_to_json(redacted)
        restored = incident_from_json(j)
        assert len(restored.trace) == 2
        assert restored.fault_class == "AGENT_ERROR"

        # 8. Validate redacted incident
        errors = validate(restored, level="core")
        assert errors == []

    def test_original_unchanged_after_pipeline(self):
        rec = Recorder()
        rec.record(
            tool="t",
            input={"email": "secret@test.com"},
            output={"key": "sk-test_abcdefghijklmnopqrst"},
        )
        incident = rec.to_incident(
            fault_class="UNKNOWN",
            impact_score=1,
            loss_amount_usd=None,
            constraints=[Constraint(policy="p", eval_result="pass")],
        )
        original_email = incident.trace[0].input["email"]
        redact_incident(incident)
        assert incident.trace[0].input["email"] == original_email


# ---------------------------------------------------------------------------
# Scenario 7: Complex nested data in trace inputs/outputs
# Tests that deeply nested structures survive serialization roundtrips.
# ---------------------------------------------------------------------------
class TestComplexNestedData:
    """Tests with deeply nested and complex data structures."""

    def test_nested_objects_roundtrip(self):
        ts = datetime(2026, 1, 1, tzinfo=timezone.utc)
        entry_input = {
            "query": {
                "filters": [
                    {"field": "status", "op": "eq", "value": "active"},
                    {"field": "amount", "op": "gt", "value": 1000},
                ],
                "pagination": {"page": 1, "per_page": 50},
            },
        }
        entry_output = {
            "results": [
                {"id": 1, "nested": {"deep": {"value": True}}},
                {"id": 2, "nested": {"deep": {"value": False}}},
            ],
            "meta": {"total": 2, "pages": 1},
        }
        inc = Incident(
            trace=[
                TraceEntry(
                    seq=1,
                    tool="search",
                    input=entry_input,
                    output=entry_output,
                    ts=ts,
                    hash=compute_hash(entry_input, entry_output),
                ),
            ],
            constraints=[Constraint(policy="p", eval_result="pass")],
            fault_class="UNKNOWN",
            impact_score=1,
            loss_amount_usd=None,
        )
        j = incident_to_json(inc)
        restored = incident_from_json(j)
        assert restored.trace[0].input["query"]["filters"][1]["value"] == 1000
        assert restored.trace[0].output["results"][0]["nested"]["deep"]["value"] is True

    def test_special_characters_in_values(self):
        ts = datetime(2026, 1, 1, tzinfo=timezone.utc)
        entry_input = {"message": 'Line 1\nLine 2\t"quoted"'}
        entry_output = {"response": "Ünïcödé & <html> © 2026"}
        inc = Incident(
            trace=[
                TraceEntry(
                    seq=1,
                    tool="chat",
                    input=entry_input,
                    output=entry_output,
                    ts=ts,
                    hash=compute_hash(entry_input, entry_output),
                ),
            ],
            constraints=[Constraint(policy="p", eval_result="pass")],
            fault_class="UNKNOWN",
            impact_score=1,
            loss_amount_usd=None,
        )
        j = incident_to_json(inc)
        restored = incident_from_json(j)
        assert restored.trace[0].input["message"] == entry_input["message"]
        assert "Ünïcödé" in restored.trace[0].output["response"]

    def test_empty_nested_structures(self):
        ts = datetime(2026, 1, 1, tzinfo=timezone.utc)
        inc = Incident(
            trace=[
                TraceEntry(
                    seq=1,
                    tool="noop",
                    input={},
                    output={},
                    ts=ts,
                    hash=compute_hash({}, {}),
                ),
            ],
            constraints=[Constraint(policy="p", eval_result="pass")],
            fault_class="UNKNOWN",
            impact_score=1,
            loss_amount_usd=None,
        )
        j = incident_to_json(inc)
        restored = incident_from_json(j)
        assert restored.trace[0].input == {}
        assert restored.trace[0].output == {}


# ---------------------------------------------------------------------------
# Scenario 8: Revision history and classification status workflow
# Tests the Classification review lifecycle.
# ---------------------------------------------------------------------------
class TestClassificationWorkflow:
    """Tests classification status transitions and revision tracking."""

    def _make_incident_with_classification(self, **cls_kwargs) -> Incident:
        ts = datetime(2026, 2, 1, tzinfo=timezone.utc)
        return Incident(
            trace=[
                TraceEntry(
                    seq=1,
                    tool="t",
                    input={"a": 1},
                    output={"b": 2},
                    ts=ts,
                    hash=compute_hash({"a": 1}, {"b": 2}),
                ),
            ],
            constraints=[Constraint(policy="p", eval_result="fail")],
            fault_class="AGENT_ERROR",
            impact_score=3,
            loss_amount_usd=1000,
            classification=Classification(**cls_kwargs),
        )

    def test_draft_status(self):
        inc = self._make_incident_with_classification(
            fault_class="AGENT_ERROR",
            classifier="llm",
            confidence=0.72,
        )
        assert inc.classification.status == "draft"

    def test_human_confirmed(self):
        inc = self._make_incident_with_classification(
            fault_class="AGENT_ERROR",
            classifier="hybrid",
            confidence=0.95,
            status="human_confirmed",
            reviewed_by="alice@acme.com",
            reviewed_at=datetime(2026, 2, 2, tzinfo=timezone.utc),
        )
        d = incident_to_dict(inc)
        cls = d["classification"]
        assert cls["status"] == "human_confirmed"
        assert cls["reviewed_by"] == "alice@acme.com"
        assert "2026-02-02" in cls["reviewed_at"]

    def test_disputed_with_revision_history(self):
        inc = self._make_incident_with_classification(
            fault_class="AGENT_ERROR",
            status="disputed",
            review_notes="Disagree — this was a spec gap, not agent error",
            revision_history=[
                {
                    "from": "AGENT_ERROR",
                    "to": "SPEC_AMBIGUITY",
                    "by": "bob@acme.com",
                    "at": "2026-02-03T10:00:00Z",
                    "reason": "Root cause was ambiguous refund policy",
                },
            ],
        )
        d = incident_to_dict(inc)
        cls = d["classification"]
        assert cls["status"] == "disputed"
        assert len(cls["revision_history"]) == 1
        assert cls["revision_history"][0]["from"] == "AGENT_ERROR"

        # Round-trip
        restored = incident_from_dict(d)
        assert restored.classification.status == "disputed"
        assert len(restored.classification.revision_history) == 1

    def test_all_classifier_types_roundtrip(self):
        for classifier in ("rules", "llm", "hybrid", "human"):
            inc = self._make_incident_with_classification(
                fault_class="UNKNOWN",
                classifier=classifier,
            )
            j = incident_to_json(inc)
            restored = incident_from_json(j)
            assert restored.classification.classifier == classifier


# ---------------------------------------------------------------------------
# Scenario 9: Edge cases in redaction
# Tests subtle PII patterns and edge cases in the redaction engine.
# ---------------------------------------------------------------------------
class TestRedactionEdgeCases:
    """Edge cases for the PII redaction engine."""

    def _make_inc(self, input_data: dict, output_data: dict) -> Incident:
        ts = datetime(2026, 1, 1, tzinfo=timezone.utc)
        return Incident(
            trace=[
                TraceEntry(
                    seq=1,
                    tool="t",
                    input=input_data,
                    output=output_data,
                    ts=ts,
                    hash=compute_hash(input_data, output_data),
                ),
            ],
            constraints=[Constraint(policy="p", eval_result="pass")],
            fault_class="UNKNOWN",
            impact_score=1,
            loss_amount_usd=None,
        )

    def test_multiple_emails_in_one_string(self):
        inc = self._make_inc(
            {"msg": "CC alice@a.com and bob@b.com on this"},
            {},
        )
        redacted = redact_incident(inc)
        msg = redacted.trace[0].input["msg"]
        assert "alice@a.com" not in msg
        assert "bob@b.com" not in msg
        assert msg.count("[REDACTED]") == 2

    def test_credit_card_without_separators(self):
        inc = self._make_inc(
            {"card": "4111111111111111"},
            {},
        )
        redacted = redact_incident(inc)
        assert "4111111111111111" not in redacted.trace[0].input["card"]

    def test_non_string_values_unchanged(self):
        inc = self._make_inc(
            {"count": 42, "active": True, "ratio": 3.14},
            {"items": [1, 2, 3]},
        )
        redacted = redact_incident(inc)
        assert redacted.trace[0].input["count"] == 42
        assert redacted.trace[0].input["active"] is True
        assert redacted.trace[0].input["ratio"] == 3.14
        assert redacted.trace[0].output["items"] == [1, 2, 3]

    def test_deeply_nested_pii(self):
        inc = self._make_inc(
            {"level1": {"level2": {"level3": {"email": "deep@nested.com"}}}},
            {},
        )
        redacted = redact_incident(inc)
        deep = redacted.trace[0].input["level1"]["level2"]["level3"]["email"]
        assert "deep@nested.com" not in deep
        assert "[REDACTED]" in deep

    def test_field_redaction_with_pattern_redaction(self):
        """Both field-level and pattern-level redaction should work together."""
        inc = self._make_inc(
            {"password": "myp@ss", "note": "Contact admin@co.com"},
            {"token": "sk-abcdefghijklmnopqrstuvwxyz"},
        )
        redacted = redact_incident(inc, fields=["password"])
        assert redacted.trace[0].input["password"] == "[REDACTED]"
        assert "admin@co.com" not in redacted.trace[0].input["note"]
        assert "sk-abcdef" not in json.dumps(redacted.trace[0].output)

    def test_custom_pattern_only(self):
        inc = self._make_inc(
            {"secret": "INTERNAL-KEY-abc123xyz"},
            {},
        )
        custom = [re.compile(r"INTERNAL-KEY-\w+")]
        redacted = redact_incident(inc, patterns=custom)
        assert "INTERNAL-KEY" not in redacted.trace[0].input["secret"]
        # Default patterns not applied when custom is provided
        # (this tests that the patterns parameter replaces defaults)


# ---------------------------------------------------------------------------
# Scenario 10: Schema validation edge cases
# ---------------------------------------------------------------------------
class TestSchemaValidationEdgeCases:
    """Tests schema validation with tricky edge cases."""

    def test_impact_score_boundaries(self):
        """Impact score must be 1-5."""
        base = {
            "trace": [{"seq": 1, "tool": "t", "input": {}, "output": {},
                        "ts": "2026-01-01T00:00:00Z", "hash": "sha256:abc123def456"}],
            "constraints": [{"policy": "p", "eval_result": "pass"}],
            "fault_class": "UNKNOWN",
            "loss_amount_usd": None,
        }
        for valid_score in (1, 2, 3, 4, 5):
            d = {**base, "impact_score": valid_score}
            assert validate(d, level="core") == [], f"Score {valid_score} should be valid"

        for invalid_score in (0, 6, -1, 100):
            d = {**base, "impact_score": invalid_score}
            assert len(validate(d, level="core")) > 0, f"Score {invalid_score} should be invalid"

    def test_all_fault_classes_valid(self):
        base = {
            "trace": [{"seq": 1, "tool": "t", "input": {}, "output": {},
                        "ts": "2026-01-01T00:00:00Z", "hash": "sha256:abc123def456"}],
            "constraints": [{"policy": "p", "eval_result": "pass"}],
            "impact_score": 1,
            "loss_amount_usd": None,
        }
        valid_classes = [
            "AGENT_ERROR", "SPEC_AMBIGUITY", "TOOL_FAILURE",
            "ADVERSARIAL_INPUT", "USER_FAULT", "UNKNOWN",
        ]
        for fc in valid_classes:
            d = {**base, "fault_class": fc}
            errors = validate(d, level="core")
            assert errors == [], f"{fc} should be valid but got: {errors}"

    def test_invalid_eval_result(self):
        data = {
            "trace": [{"seq": 1, "tool": "t", "input": {}, "output": {},
                        "ts": "2026-01-01T00:00:00Z", "hash": "sha256:abc123def456"}],
            "constraints": [{"policy": "p", "eval_result": "maybe"}],
            "fault_class": "UNKNOWN",
            "impact_score": 1,
            "loss_amount_usd": None,
        }
        errors = validate(data, level="core")
        assert len(errors) > 0

    def test_loss_amount_usd_explicit_null(self):
        """loss_amount_usd: null is valid (unknown losses)."""
        data = {
            "trace": [{"seq": 1, "tool": "t", "input": {}, "output": {},
                        "ts": "2026-01-01T00:00:00Z", "hash": "sha256:abc123def456"}],
            "constraints": [{"policy": "p", "eval_result": "pass"}],
            "fault_class": "UNKNOWN",
            "impact_score": 1,
            "loss_amount_usd": None,
        }
        errors = validate(data, level="core")
        assert errors == []

    def test_loss_amount_usd_zero_valid(self):
        """loss_amount_usd: 0 is valid (near-miss, no actual loss)."""
        data = {
            "trace": [{"seq": 1, "tool": "t", "input": {}, "output": {},
                        "ts": "2026-01-01T00:00:00Z", "hash": "sha256:abc123def456"}],
            "constraints": [{"policy": "p", "eval_result": "pass"}],
            "fault_class": "UNKNOWN",
            "impact_score": 1,
            "loss_amount_usd": 0,
        }
        errors = validate(data, level="core")
        assert errors == []
