"""Report generation — 4-section Core report."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from .templates import (
    AUTO_CLASSIFY_NOTE,
    CLASSIFICATION_EXTRA,
    EXECUTIVE_SUMMARY,
    FAULT_CLASSIFICATION_HEADER,
    IMPACT_ASSESSMENT_HEADER,
    IMPACT_CRITERIA,
    IMPACT_LABELS,
    LOSS_BREAKDOWN_HEADER,
    LOSS_BREAKDOWN_ROW,
    LOSS_BREAKDOWN_TOTAL,
    REPORT_FOOTER,
    REPORT_HEADER,
    TIMELINE_HEADER,
    TIMELINE_ROW,
)


def _one_line_summary(entry: dict[str, Any], max_len: int = 80) -> str:
    """Generate a one-line summary of a trace entry's input/output."""
    parts = []

    inp = entry.get("input", {})
    if isinstance(inp, dict):
        for k, v in list(inp.items())[:3]:
            parts.append(f"{k}={v}")

    out = entry.get("output", {})
    if isinstance(out, dict):
        out_parts = []
        for k, v in list(out.items())[:2]:
            out_parts.append(f"{v}")
        if out_parts:
            parts.append("-> " + ", ".join(out_parts))

    summary = ", ".join(parts) if parts else "—"
    if len(summary) > max_len:
        summary = summary[: max_len - 3] + "..."
    return summary


def generate_report(data: dict[str, Any]) -> str:
    """Generate a 4-section markdown report from an incident dict.

    Returns the full markdown string.
    """
    auto_classified = False
    confidence = 0.0

    # Attempt auto-classification if fault_class is UNKNOWN
    if data.get("fault_class") == "UNKNOWN":
        try:
            from agentincident_classifier import classify

            result = classify(data)
            data = dict(data)  # shallow copy to avoid mutating input
            data["fault_class"] = result.fault_class
            auto_classified = True
            confidence = result.confidence
        except ImportError:
            pass

    trace = data.get("trace", [])
    constraints = data.get("constraints", [])
    meta = data.get("meta", {}) or {}
    classification = data.get("classification", {}) or {}
    loss_estimate = data.get("loss_estimate")
    fault_class = data.get("fault_class", "UNKNOWN")
    impact_score = data.get("impact_score", 1)
    loss_amount_usd = data.get("loss_amount_usd")

    impact_label = IMPACT_LABELS.get(impact_score, "Unknown")
    impact_criteria = IMPACT_CRITERIA.get(impact_score, "")

    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # Header
    incident_id = meta.get("incident_id", "Unidentified")
    status = classification.get("status", "DRAFT").upper()
    sections = [REPORT_HEADER.format(
        incident_id=incident_id,
        generated_at=now_iso,
        status=status,
    )]

    # Section 1: Executive Summary
    incident_date = "an unknown date"
    if trace:
        ts_str = trace[0].get("ts", "")
        if ts_str:
            try:
                dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                incident_date = dt.strftime("%Y-%m-%d")
            except (ValueError, TypeError):
                incident_date = ts_str[:10] if len(ts_str) >= 10 else ts_str

    agent_desc = meta.get("agent") or "an agent"

    pass_count = sum(1 for c in constraints if c.get("eval_result") == "pass")
    fail_count = sum(1 for c in constraints if c.get("eval_result") == "fail")
    constraint_summary = (
        f"{len(constraints)} constraint(s) were evaluated "
        f"({pass_count} passed, {fail_count} failed)."
    )

    # Loss sentence
    loss_sentence = ""
    if loss_amount_usd is not None:
        loss_sentence = f" Confirmed loss: ${loss_amount_usd:,.2f}."
    elif loss_estimate and isinstance(loss_estimate, dict):
        total = loss_estimate.get("total_usd")
        if total is not None:
            loss_sentence = f" Estimated loss: ${total:,.2f}."

    sections.append("")
    sections.append(EXECUTIVE_SUMMARY.format(
        incident_date=incident_date,
        agent_desc=agent_desc,
        trace_count=len(trace),
        constraint_summary=constraint_summary,
        fault_class=fault_class,
        impact_score=impact_score,
        impact_label=impact_label,
        loss_sentence=loss_sentence,
    ))

    if auto_classified:
        sections.append(AUTO_CLASSIFY_NOTE.format(confidence=confidence))

    # Section 2: Timeline
    sections.append("")
    sections.append(TIMELINE_HEADER)
    for entry in trace:
        ts = entry.get("ts", "—")
        tool = entry.get("tool", "unknown")
        details = _one_line_summary(entry)
        sections.append(TIMELINE_ROW.format(ts=ts, tool=tool, details=details))

    # Section 3: Fault Classification
    loss_display = f"${loss_amount_usd:,.2f}" if loss_amount_usd is not None else "Not confirmed"

    sections.append("")
    sections.append(FAULT_CLASSIFICATION_HEADER.format(
        fault_class=fault_class,
        impact_score=impact_score,
        impact_label=impact_label,
        loss_display=loss_display,
    ))

    if classification:
        conf = classification.get("confidence")
        classifier = classification.get("classifier")
        if conf is not None or classifier is not None:
            sections.append(CLASSIFICATION_EXTRA.format(
                confidence=conf if conf is not None else "—",
                classifier=classifier or "—",
            ))

    # Section 4: Impact Assessment
    sections.append("")
    sections.append(IMPACT_ASSESSMENT_HEADER.format(
        impact_label=impact_label,
        impact_criteria=impact_criteria,
    ))

    if loss_estimate and isinstance(loss_estimate, dict):
        breakdown = loss_estimate.get("breakdown", {})
        if breakdown:
            sections.append(LOSS_BREAKDOWN_HEADER)
            for category, amount in breakdown.items():
                amount_str = f"${amount:,.2f}" if amount is not None else "—"
                sections.append(LOSS_BREAKDOWN_ROW.format(
                    category=category, amount=amount_str,
                ))
            total = loss_estimate.get("total_usd")
            if total is not None:
                sections.append(LOSS_BREAKDOWN_TOTAL.format(total=total))

    # Footer
    sections.append(REPORT_FOOTER)

    return "\n".join(sections)
