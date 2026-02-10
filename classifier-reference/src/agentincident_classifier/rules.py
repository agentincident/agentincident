"""Priority-ordered rules engine for fault classification."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .signals import (
    extract_constraint_signals,
    extract_error_signals,
    extract_timing_anomalies,
)


@dataclass(slots=True)
class ClassificationResult:
    """Result of running the reference classifier."""

    fault_class: str
    confidence: float
    evidence: list[str]
    rule_name: str


# Injection markers for adversarial input detection
_INJECTION_MARKERS = [
    "ignore previous",
    "ignore above",
    "ignore all previous",
    "system:",
    "<|im_start|>",
    "<|im_end|>",
    "<|endoftext|>",
    "you are now",
    "new instructions:",
    "disregard",
    "forget your instructions",
    "act as",
]


def _check_tool_error(
    trace: list[dict[str, Any]],
    constraints: list[dict[str, Any]],
) -> ClassificationResult | None:
    """Rule 1: Tool error — output has error/exception keys or HTTP error status."""
    errors = extract_error_signals(trace)
    if errors:
        details = [f"Tool `{e['tool']}` (seq {e['seq']}): {e['detail']}" for e in errors]
        return ClassificationResult(
            fault_class="TOOL_FAILURE",
            confidence=0.85,
            evidence=details,
            rule_name="tool_error",
        )
    return None


def _check_tool_timeout(
    trace: list[dict[str, Any]],
    constraints: list[dict[str, Any]],
) -> ClassificationResult | None:
    """Rule 2: Tool timeout — duration_ms > 30s or output contains 'timeout'."""
    anomalies = extract_timing_anomalies(trace)
    if anomalies:
        details = [
            f"Tool `{a['tool']}` (seq {a['seq']}): {a['reason']}"
            + (f" ({a['duration_ms']}ms)" if a.get("duration_ms") else "")
            for a in anomalies
        ]
        return ClassificationResult(
            fault_class="TOOL_FAILURE",
            confidence=0.80,
            evidence=details,
            rule_name="tool_timeout",
        )
    return None


def _check_constraint_failed(
    trace: list[dict[str, Any]],
    constraints: list[dict[str, Any]],
) -> ClassificationResult | None:
    """Rule 3: Constraint failed — any constraint has eval_result == 'fail'."""
    signals = extract_constraint_signals(constraints)
    if signals["failed"] > 0:
        details = [
            f"{signals['failed']}/{signals['total']} constraint(s) failed",
            f"Failed policies: {', '.join(signals['failed_policies'])}",
        ]
        return ClassificationResult(
            fault_class="AGENT_ERROR",
            confidence=0.75,
            evidence=details,
            rule_name="constraint_failed",
        )
    return None


def _check_adversarial_input(
    trace: list[dict[str, Any]],
    constraints: list[dict[str, Any]],
) -> ClassificationResult | None:
    """Rule 4: Adversarial input — trace inputs contain injection markers."""
    found = []
    for entry in trace:
        inp = entry.get("input", {})
        if not isinstance(inp, dict):
            continue
        input_str = str(inp).lower()
        for marker in _INJECTION_MARKERS:
            if marker in input_str:
                found.append(
                    f"Tool `{entry.get('tool')}` (seq {entry.get('seq')}): "
                    f"input contains injection marker '{marker}'"
                )
                break
    if found:
        return ClassificationResult(
            fault_class="ADVERSARIAL_INPUT",
            confidence=0.60,
            evidence=found,
            rule_name="adversarial_input",
        )
    return None


def _check_constraint_gap(
    trace: list[dict[str, Any]],
    constraints: list[dict[str, Any]],
) -> ClassificationResult | None:
    """Rule 5: Constraint gap — any constraint has non-empty gaps_identified."""
    signals = extract_constraint_signals(constraints)
    if signals["has_gaps"]:
        details = [f"Policy gaps identified: {', '.join(signals['gaps'])}"]
        return ClassificationResult(
            fault_class="SPEC_AMBIGUITY",
            confidence=0.70,
            evidence=details,
            rule_name="constraint_gap",
        )
    return None


def _check_all_passed(
    trace: list[dict[str, Any]],
    constraints: list[dict[str, Any]],
) -> ClassificationResult | None:
    """Rule 6: All passed — all constraints passed, no tool errors."""
    signals = extract_constraint_signals(constraints)
    errors = extract_error_signals(trace)
    if signals["failed"] == 0 and len(errors) == 0:
        return ClassificationResult(
            fault_class="SPEC_AMBIGUITY",
            confidence=0.55,
            evidence=[
                f"All {signals['total']} constraint(s) passed",
                "No tool errors detected",
                "Incident occurred despite passing constraints — likely spec gap",
            ],
            rule_name="all_passed",
        )
    return None


def _default_rule(
    trace: list[dict[str, Any]],
    constraints: list[dict[str, Any]],
) -> ClassificationResult:
    """Rule 7: Default — no other rule matched."""
    return ClassificationResult(
        fault_class="UNKNOWN",
        confidence=0.30,
        evidence=["No classification rule matched the incident data"],
        rule_name="default",
    )


# Rules in priority order
_RULES = [
    _check_tool_error,
    _check_tool_timeout,
    _check_constraint_failed,
    _check_adversarial_input,
    _check_constraint_gap,
    _check_all_passed,
]


def classify(incident: Any) -> ClassificationResult:
    """Classify an incident using the reference rules engine.

    Accepts either an Incident dataclass or a dict with 'trace' and 'constraints' keys.

    USER_FAULT is never returned — requires human context.
    """
    # Support both dict and Incident object input
    if isinstance(incident, dict):
        trace = incident.get("trace", [])
        constraints = incident.get("constraints", [])
    else:
        # Assume it's an Incident-like object
        from agentincident.export import incident_to_dict

        d = incident_to_dict(incident)
        trace = d.get("trace", [])
        constraints = d.get("constraints", [])

    for rule_fn in _RULES:
        result = rule_fn(trace, constraints)
        if result is not None:
            return result

    return _default_rule(trace, constraints)
