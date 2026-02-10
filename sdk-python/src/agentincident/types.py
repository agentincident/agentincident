from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class TraceEntry:
    seq: int
    tool: str
    input: dict[str, Any]
    output: dict[str, Any]
    ts: datetime
    hash: str
    duration_ms: int | None = None
    irreversible: bool = False
    agent_reasoning: str | None = None


@dataclass(slots=True)
class Constraint:
    policy: str
    eval_result: str  # "pass" | "fail"
    version: str | None = None
    breach_delta: float | None = None
    gaps_identified: list[str] = field(default_factory=list)


@dataclass(slots=True)
class Meta:
    schema: str = "agentincident/v0.1"
    incident_id: str | None = None
    incident_type: str = "INCIDENT"
    created_at: datetime | None = None
    updated_at: datetime | None = None
    agent: str | None = None
    framework: str | None = None
    environment: str | None = None
    trigger: str | None = None


@dataclass(slots=True)
class Classification:
    fault_class: str
    fault_subclass: str | None = None
    fault_vector: str | None = None
    confidence: float | None = None
    classifier: str | None = None
    status: str = "draft"
    reviewed_by: str | None = None
    reviewed_at: datetime | None = None
    evidence: list[str] = field(default_factory=list)
    counterfactuals: list[str] = field(default_factory=list)
    review_notes: str | None = None
    revision_history: list[dict[str, Any]] = field(default_factory=list)


@dataclass(slots=True)
class Liability:
    primary: str
    contributing: list[str] = field(default_factory=list)
    policy_owner: str | None = None


@dataclass(slots=True)
class LossEstimate:
    total_usd: float
    confidence: str = "medium"
    breakdown: dict[str, float | None] = field(default_factory=dict)


@dataclass(slots=True)
class ResponseAction:
    description: str
    status: str
    owner: str | None = None
    completed_at: datetime | None = None


@dataclass(slots=True)
class Verification:
    test: str
    method: str
    result: str


@dataclass(slots=True)
class ConstraintUpdate:
    from_policy: str  # "from" in JSON
    to_policy: str  # "to" in JSON
    diff: dict[str, Any] | None = None
    deployed_at: datetime | None = None


@dataclass(slots=True)
class Response:
    actions: list[ResponseAction] = field(default_factory=list)
    constraint_update: ConstraintUpdate | None = None
    verification: list[Verification] = field(default_factory=list)
    time_to_detect_sec: int | None = None
    time_to_contain_sec: int | None = None
    time_to_remediate_sec: int | None = None


@dataclass(slots=True)
class Incident:
    trace: list[TraceEntry]
    constraints: list[Constraint]
    fault_class: str
    impact_score: int
    loss_amount_usd: float | None
    meta: Meta | None = None
    classification: Classification | None = None
    liability: Liability | None = None
    loss_estimate: LossEstimate | None = None
    response: Response | None = None
