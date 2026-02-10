"""Tests for export/serialization functions."""
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
    compute_hash,
    incident_from_dict,
    incident_from_json,
    incident_to_dict,
    incident_to_json,
)


def _make_full_incident() -> Incident:
    ts = datetime(2026, 2, 9, 22, 41, 7, tzinfo=timezone.utc)
    return Incident(
        trace=[
            TraceEntry(
                seq=1,
                tool="stripe.refund",
                input={"charge": "ch_9xK", "amount": 47218},
                output={"refund_id": "re_Xp7", "status": "succeeded"},
                ts=ts,
                hash=compute_hash(
                    {"charge": "ch_9xK", "amount": 47218},
                    {"refund_id": "re_Xp7", "status": "succeeded"},
                ),
                duration_ms=1204,
                irreversible=True,
            )
        ],
        constraints=[
            Constraint(
                policy="refund_policy_v3",
                eval_result="pass",
                version="3.1.0",
                breach_delta=2782,
                gaps_identified=["no cumulative_exposure constraint"],
            )
        ],
        fault_class="SPEC_AMBIGUITY",
        impact_score=4,
        loss_amount_usd=47218.00,
        meta=Meta(
            schema="agentincident/v0.1",
            incident_id="INC-2026-0247",
            incident_type="INCIDENT",
            created_at=ts,
            agent="refund-processor-v3",
            framework="langchain",
            environment="production",
        ),
        classification=Classification(
            fault_class="SPEC_AMBIGUITY",
            confidence=0.84,
            classifier="hybrid",
            status="human_confirmed",
            evidence=["Policy gap found"],
        ),
        liability=Liability(
            primary="spec_owner:payments-team@acme.com",
            contributing=["agent:selection_error"],
        ),
        loss_estimate=LossEstimate(
            total_usd=48868,
            confidence="medium",
            breakdown={"direct_cash_loss": 47218, "fees": 450},
        ),
        response=Response(
            actions=[
                ResponseAction(
                    description="Initiated dispute",
                    status="done",
                    owner="jake@acme.com",
                    completed_at=ts,
                )
            ],
            constraint_update=ConstraintUpdate(
                from_policy="refund_policy_v3",
                to_policy="refund_policy_v4",
                diff={"added": {"max_cumulative": 50000}},
                deployed_at=ts,
            ),
            verification=[
                Verification(test="replay", method="deterministic", result="pass")
            ],
            time_to_detect_sec=357,
            time_to_contain_sec=3177,
            time_to_remediate_sec=20940,
        ),
    )


class TestIncidentToDict:
    def test_minimal(self, minimal_incident):
        d = incident_to_dict(minimal_incident)
        assert d["fault_class"] == "SPEC_AMBIGUITY"
        assert d["impact_score"] == 4
        assert d["loss_amount_usd"] == 47218.00
        assert len(d["trace"]) == 1
        assert len(d["constraints"]) == 1
        assert "meta" not in d

    def test_full(self):
        inc = _make_full_incident()
        d = incident_to_dict(inc)
        assert "meta" in d
        assert "classification" in d
        assert "liability" in d
        assert "loss_estimate" in d
        assert "response" in d

    def test_constraint_update_from_to_mapping(self):
        inc = _make_full_incident()
        d = incident_to_dict(inc)
        cu = d["response"]["constraint_update"]
        # In JSON, from_policy maps to "from" and to_policy maps to "to"
        assert "from" in cu
        assert "to" in cu
        assert cu["from"] == "refund_policy_v3"
        assert cu["to"] == "refund_policy_v4"
        # Python attribute names should NOT appear in dict
        assert "from_policy" not in cu
        assert "to_policy" not in cu

    def test_none_fields_omitted(self):
        d = incident_to_dict(_make_full_incident())
        trace = d["trace"][0]
        # agent_reasoning is None, should not be in dict
        assert "agent_reasoning" not in trace

    def test_datetime_serialized(self):
        d = incident_to_dict(_make_full_incident())
        ts = d["trace"][0]["ts"]
        assert isinstance(ts, str)
        assert "2026" in ts


class TestIncidentFromDict:
    def test_roundtrip(self):
        original = _make_full_incident()
        d = incident_to_dict(original)
        restored = incident_from_dict(d)
        assert restored.fault_class == original.fault_class
        assert restored.impact_score == original.impact_score
        assert restored.loss_amount_usd == original.loss_amount_usd
        assert len(restored.trace) == len(original.trace)
        assert restored.trace[0].tool == original.trace[0].tool
        assert restored.trace[0].hash == original.trace[0].hash

    def test_from_to_mapping_roundtrip(self):
        original = _make_full_incident()
        d = incident_to_dict(original)
        restored = incident_from_dict(d)
        assert restored.response is not None
        assert restored.response.constraint_update is not None
        assert restored.response.constraint_update.from_policy == "refund_policy_v3"
        assert restored.response.constraint_update.to_policy == "refund_policy_v4"

    def test_minimal_roundtrip(self, minimal_incident):
        d = incident_to_dict(minimal_incident)
        restored = incident_from_dict(d)
        assert restored.fault_class == minimal_incident.fault_class
        assert restored.meta is None
        assert restored.classification is None


class TestJsonSerialization:
    def test_to_json(self):
        inc = _make_full_incident()
        j = incident_to_json(inc)
        assert '"fault_class"' in j
        assert '"SPEC_AMBIGUITY"' in j

    def test_from_json(self):
        inc = _make_full_incident()
        j = incident_to_json(inc)
        restored = incident_from_json(j)
        assert restored.fault_class == inc.fault_class
        assert restored.impact_score == inc.impact_score

    def test_json_roundtrip(self):
        original = _make_full_incident()
        j = incident_to_json(original)
        restored = incident_from_json(j)
        j2 = incident_to_json(restored)
        assert j == j2
