from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from .types import (
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


def _dt_to_str(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    return dt.isoformat()


def _str_to_dt(s: str | None) -> datetime | None:
    if s is None:
        return None
    return datetime.fromisoformat(s)


def _omit_none(d: dict[str, Any]) -> dict[str, Any]:
    """Remove keys with None values from a dict."""
    return {k: v for k, v in d.items() if v is not None}


def _trace_entry_to_dict(entry: TraceEntry) -> dict[str, Any]:
    d: dict[str, Any] = {
        "seq": entry.seq,
        "tool": entry.tool,
        "input": entry.input,
        "output": entry.output,
        "ts": _dt_to_str(entry.ts),
        "hash": entry.hash,
    }
    if entry.duration_ms is not None:
        d["duration_ms"] = entry.duration_ms
    if entry.irreversible:
        d["irreversible"] = entry.irreversible
    if entry.agent_reasoning is not None:
        d["agent_reasoning"] = entry.agent_reasoning
    return d


def _trace_entry_from_dict(data: dict[str, Any]) -> TraceEntry:
    return TraceEntry(
        seq=data["seq"],
        tool=data["tool"],
        input=data["input"],
        output=data["output"],
        ts=_str_to_dt(data["ts"]),  # type: ignore[arg-type]
        hash=data["hash"],
        duration_ms=data.get("duration_ms"),
        irreversible=data.get("irreversible", False),
        agent_reasoning=data.get("agent_reasoning"),
    )


def _constraint_to_dict(c: Constraint) -> dict[str, Any]:
    d: dict[str, Any] = {
        "policy": c.policy,
        "eval_result": c.eval_result,
    }
    if c.version is not None:
        d["version"] = c.version
    if c.breach_delta is not None:
        d["breach_delta"] = c.breach_delta
    if c.gaps_identified:
        d["gaps_identified"] = c.gaps_identified
    return d


def _constraint_from_dict(data: dict[str, Any]) -> Constraint:
    return Constraint(
        policy=data["policy"],
        eval_result=data["eval_result"],
        version=data.get("version"),
        breach_delta=data.get("breach_delta"),
        gaps_identified=data.get("gaps_identified", []),
    )


def _meta_to_dict(m: Meta) -> dict[str, Any]:
    d: dict[str, Any] = {"schema": m.schema}
    if m.incident_id is not None:
        d["incident_id"] = m.incident_id
    d["incident_type"] = m.incident_type
    if m.created_at is not None:
        d["created_at"] = _dt_to_str(m.created_at)
    if m.updated_at is not None:
        d["updated_at"] = _dt_to_str(m.updated_at)
    if m.agent is not None:
        d["agent"] = m.agent
    if m.framework is not None:
        d["framework"] = m.framework
    if m.environment is not None:
        d["environment"] = m.environment
    if m.trigger is not None:
        d["trigger"] = m.trigger
    return d


def _meta_from_dict(data: dict[str, Any]) -> Meta:
    return Meta(
        schema=data.get("schema", "agentincident/v0.1"),
        incident_id=data.get("incident_id"),
        incident_type=data.get("incident_type", "INCIDENT"),
        created_at=_str_to_dt(data.get("created_at")),
        updated_at=_str_to_dt(data.get("updated_at")),
        agent=data.get("agent"),
        framework=data.get("framework"),
        environment=data.get("environment"),
        trigger=data.get("trigger"),
    )


def _classification_to_dict(c: Classification) -> dict[str, Any]:
    d: dict[str, Any] = {"fault_class": c.fault_class}
    if c.fault_subclass is not None:
        d["fault_subclass"] = c.fault_subclass
    if c.fault_vector is not None:
        d["fault_vector"] = c.fault_vector
    if c.confidence is not None:
        d["confidence"] = c.confidence
    if c.classifier is not None:
        d["classifier"] = c.classifier
    d["status"] = c.status
    if c.reviewed_by is not None:
        d["reviewed_by"] = c.reviewed_by
    if c.reviewed_at is not None:
        d["reviewed_at"] = _dt_to_str(c.reviewed_at)
    if c.evidence:
        d["evidence"] = c.evidence
    if c.counterfactuals:
        d["counterfactuals"] = c.counterfactuals
    if c.review_notes is not None:
        d["review_notes"] = c.review_notes
    if c.revision_history:
        d["revision_history"] = c.revision_history
    return d


def _classification_from_dict(data: dict[str, Any]) -> Classification:
    return Classification(
        fault_class=data["fault_class"],
        fault_subclass=data.get("fault_subclass"),
        fault_vector=data.get("fault_vector"),
        confidence=data.get("confidence"),
        classifier=data.get("classifier"),
        status=data.get("status", "draft"),
        reviewed_by=data.get("reviewed_by"),
        reviewed_at=_str_to_dt(data.get("reviewed_at")),
        evidence=data.get("evidence", []),
        counterfactuals=data.get("counterfactuals", []),
        review_notes=data.get("review_notes"),
        revision_history=data.get("revision_history", []),
    )


def _liability_to_dict(l: Liability) -> dict[str, Any]:
    d: dict[str, Any] = {"primary": l.primary}
    if l.contributing:
        d["contributing"] = l.contributing
    if l.policy_owner is not None:
        d["policy_owner"] = l.policy_owner
    return d


def _liability_from_dict(data: dict[str, Any]) -> Liability:
    return Liability(
        primary=data["primary"],
        contributing=data.get("contributing", []),
        policy_owner=data.get("policy_owner"),
    )


def _loss_estimate_to_dict(le: LossEstimate) -> dict[str, Any]:
    d: dict[str, Any] = {
        "total_usd": le.total_usd,
        "confidence": le.confidence,
    }
    if le.breakdown:
        d["breakdown"] = le.breakdown
    return d


def _loss_estimate_from_dict(data: dict[str, Any]) -> LossEstimate:
    return LossEstimate(
        total_usd=data["total_usd"],
        confidence=data.get("confidence", "medium"),
        breakdown=data.get("breakdown", {}),
    )


def _response_action_to_dict(ra: ResponseAction) -> dict[str, Any]:
    d: dict[str, Any] = {
        "description": ra.description,
        "status": ra.status,
    }
    if ra.owner is not None:
        d["owner"] = ra.owner
    if ra.completed_at is not None:
        d["completed_at"] = _dt_to_str(ra.completed_at)
    return d


def _response_action_from_dict(data: dict[str, Any]) -> ResponseAction:
    return ResponseAction(
        description=data["description"],
        status=data["status"],
        owner=data.get("owner"),
        completed_at=_str_to_dt(data.get("completed_at")),
    )


def _verification_to_dict(v: Verification) -> dict[str, Any]:
    return {
        "test": v.test,
        "method": v.method,
        "result": v.result,
    }


def _verification_from_dict(data: dict[str, Any]) -> Verification:
    return Verification(
        test=data["test"],
        method=data["method"],
        result=data["result"],
    )


def _constraint_update_to_dict(cu: ConstraintUpdate) -> dict[str, Any]:
    d: dict[str, Any] = {
        "from": cu.from_policy,
        "to": cu.to_policy,
    }
    if cu.diff is not None:
        d["diff"] = cu.diff
    if cu.deployed_at is not None:
        d["deployed_at"] = _dt_to_str(cu.deployed_at)
    return d


def _constraint_update_from_dict(data: dict[str, Any]) -> ConstraintUpdate:
    return ConstraintUpdate(
        from_policy=data["from"],
        to_policy=data["to"],
        diff=data.get("diff"),
        deployed_at=_str_to_dt(data.get("deployed_at")),
    )


def _response_to_dict(r: Response) -> dict[str, Any]:
    d: dict[str, Any] = {}
    if r.actions:
        d["actions"] = [_response_action_to_dict(a) for a in r.actions]
    if r.constraint_update is not None:
        d["constraint_update"] = _constraint_update_to_dict(r.constraint_update)
    if r.verification:
        d["verification"] = [_verification_to_dict(v) for v in r.verification]
    if r.time_to_detect_sec is not None:
        d["time_to_detect_sec"] = r.time_to_detect_sec
    if r.time_to_contain_sec is not None:
        d["time_to_contain_sec"] = r.time_to_contain_sec
    if r.time_to_remediate_sec is not None:
        d["time_to_remediate_sec"] = r.time_to_remediate_sec
    return d


def _response_from_dict(data: dict[str, Any]) -> Response:
    return Response(
        actions=[_response_action_from_dict(a) for a in data.get("actions", [])],
        constraint_update=(
            _constraint_update_from_dict(data["constraint_update"])
            if "constraint_update" in data
            else None
        ),
        verification=[_verification_from_dict(v) for v in data.get("verification", [])],
        time_to_detect_sec=data.get("time_to_detect_sec"),
        time_to_contain_sec=data.get("time_to_contain_sec"),
        time_to_remediate_sec=data.get("time_to_remediate_sec"),
    )


def incident_to_dict(incident: Incident) -> dict[str, Any]:
    """Convert an Incident dataclass to a JSON-compatible dict."""
    d: dict[str, Any] = {
        "trace": [_trace_entry_to_dict(e) for e in incident.trace],
        "constraints": [_constraint_to_dict(c) for c in incident.constraints],
        "fault_class": incident.fault_class,
        "impact_score": incident.impact_score,
        "loss_amount_usd": incident.loss_amount_usd,
    }
    if incident.meta is not None:
        d["meta"] = _meta_to_dict(incident.meta)
    if incident.classification is not None:
        d["classification"] = _classification_to_dict(incident.classification)
    if incident.liability is not None:
        d["liability"] = _liability_to_dict(incident.liability)
    if incident.loss_estimate is not None:
        d["loss_estimate"] = _loss_estimate_to_dict(incident.loss_estimate)
    if incident.response is not None:
        d["response"] = _response_to_dict(incident.response)
    return d


def incident_from_dict(data: dict[str, Any]) -> Incident:
    """Construct an Incident dataclass from a dict."""
    return Incident(
        trace=[_trace_entry_from_dict(e) for e in data["trace"]],
        constraints=[_constraint_from_dict(c) for c in data["constraints"]],
        fault_class=data["fault_class"],
        impact_score=data["impact_score"],
        loss_amount_usd=data.get("loss_amount_usd"),
        meta=_meta_from_dict(data["meta"]) if "meta" in data else None,
        classification=(
            _classification_from_dict(data["classification"])
            if "classification" in data
            else None
        ),
        liability=(
            _liability_from_dict(data["liability"]) if "liability" in data else None
        ),
        loss_estimate=(
            _loss_estimate_from_dict(data["loss_estimate"])
            if "loss_estimate" in data
            else None
        ),
        response=(
            _response_from_dict(data["response"]) if "response" in data else None
        ),
    )


def incident_to_json(incident: Incident, indent: int = 2) -> str:
    """Serialize an Incident to a JSON string."""
    return json.dumps(incident_to_dict(incident), indent=indent, default=str)


def incident_from_json(json_str: str) -> Incident:
    """Deserialize an Incident from a JSON string."""
    return incident_from_dict(json.loads(json_str))
