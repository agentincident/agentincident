"""Tests for PII redaction."""
from __future__ import annotations

from datetime import datetime, timezone

from agentincident import (
    Constraint,
    Incident,
    TraceEntry,
    compute_hash,
    redact_incident,
)


def _make_incident_with_pii() -> Incident:
    ts = datetime(2026, 2, 9, 22, 41, 7, tzinfo=timezone.utc)
    return Incident(
        trace=[
            TraceEntry(
                seq=1,
                tool="email.send",
                input={
                    "to": "customer@example.com",
                    "api_key": "sk-1234567890abcdefghijklmn",
                    "message": "Refund for card 4111-1111-1111-1111",
                },
                output={
                    "status": "sent",
                    "auth": "Bearer eyJhbGciOiJIUzI1NiJ9.test",
                    "recipient": "user@test.org",
                },
                ts=ts,
                hash=compute_hash(
                    {
                        "to": "customer@example.com",
                        "api_key": "sk-1234567890abcdefghijklmn",
                        "message": "Refund for card 4111-1111-1111-1111",
                    },
                    {
                        "status": "sent",
                        "auth": "Bearer eyJhbGciOiJIUzI1NiJ9.test",
                        "recipient": "user@test.org",
                    },
                ),
            ),
            TraceEntry(
                seq=2,
                tool="clean.tool",
                input={"data": "no pii here"},
                output={"ok": True},
                ts=ts,
                hash=compute_hash(
                    {"data": "no pii here"}, {"ok": True}
                ),
            ),
        ],
        constraints=[Constraint(policy="p", eval_result="pass")],
        fault_class="AGENT_ERROR",
        impact_score=3,
        loss_amount_usd=1000,
    )


class TestRedactEmail:
    def test_email_redacted_in_input(self):
        inc = _make_incident_with_pii()
        redacted = redact_incident(inc)
        assert "[REDACTED]" in redacted.trace[0].input["to"]
        assert "customer@example.com" not in redacted.trace[0].input["to"]

    def test_email_redacted_in_output(self):
        inc = _make_incident_with_pii()
        redacted = redact_incident(inc)
        assert "[REDACTED]" in redacted.trace[0].output["recipient"]
        assert "user@test.org" not in redacted.trace[0].output["recipient"]


class TestRedactApiKey:
    def test_sk_key_redacted(self):
        inc = _make_incident_with_pii()
        redacted = redact_incident(inc)
        assert "[REDACTED]" in redacted.trace[0].input["api_key"]
        assert "sk-1234567890" not in redacted.trace[0].input["api_key"]

    def test_bearer_token_redacted(self):
        inc = _make_incident_with_pii()
        redacted = redact_incident(inc)
        assert "[REDACTED]" in redacted.trace[0].output["auth"]
        assert "eyJhbG" not in redacted.trace[0].output["auth"]


class TestRedactCreditCard:
    def test_credit_card_redacted(self):
        inc = _make_incident_with_pii()
        redacted = redact_incident(inc)
        assert "4111-1111-1111-1111" not in redacted.trace[0].input["message"]
        assert "[REDACTED]" in redacted.trace[0].input["message"]


class TestRedactHashRecomputation:
    def test_hashes_recomputed(self):
        inc = _make_incident_with_pii()
        original_hash = inc.trace[0].hash
        redacted = redact_incident(inc)
        assert redacted.trace[0].hash != original_hash
        assert redacted.trace[0].hash.startswith("sha256:")
        # Hash should match recomputed value
        expected = compute_hash(redacted.trace[0].input, redacted.trace[0].output)
        assert redacted.trace[0].hash == expected

    def test_clean_entry_unchanged_data(self):
        inc = _make_incident_with_pii()
        redacted = redact_incident(inc)
        # Clean entry data is unchanged
        assert redacted.trace[1].input == {"data": "no pii here"}
        assert redacted.trace[1].output == {"ok": True}


class TestRedactOriginalUnchanged:
    def test_original_not_mutated(self):
        inc = _make_incident_with_pii()
        original_email = inc.trace[0].input["to"]
        redact_incident(inc)
        assert inc.trace[0].input["to"] == original_email


class TestRedactCustomFields:
    def test_field_based_redaction(self):
        inc = _make_incident_with_pii()
        redacted = redact_incident(inc, fields=["to", "auth"])
        assert redacted.trace[0].input["to"] == "[REDACTED]"
        assert redacted.trace[0].output["auth"] == "[REDACTED]"
