"""Shared test fixtures for AgentIncident SDK tests."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from agentincident import (
    Constraint,
    Incident,
    Meta,
    Recorder,
    TraceEntry,
    compute_hash,
)


@pytest.fixture
def sample_trace_entry() -> TraceEntry:
    return TraceEntry(
        seq=1,
        tool="stripe.refund",
        input={"charge": "ch_9xK", "amount": 47218},
        output={"refund_id": "re_Xp7", "status": "succeeded"},
        ts=datetime(2026, 2, 9, 22, 41, 7, tzinfo=timezone.utc),
        hash=compute_hash(
            {"charge": "ch_9xK", "amount": 47218},
            {"refund_id": "re_Xp7", "status": "succeeded"},
        ),
        duration_ms=1204,
        irreversible=True,
    )


@pytest.fixture
def sample_constraint() -> Constraint:
    return Constraint(
        policy="refund_policy_v3",
        eval_result="pass",
        version="3.1.0",
        breach_delta=2782,
        gaps_identified=["no cumulative_exposure constraint"],
    )


@pytest.fixture
def minimal_incident(sample_trace_entry: TraceEntry, sample_constraint: Constraint) -> Incident:
    return Incident(
        trace=[sample_trace_entry],
        constraints=[sample_constraint],
        fault_class="SPEC_AMBIGUITY",
        impact_score=4,
        loss_amount_usd=47218.00,
    )
