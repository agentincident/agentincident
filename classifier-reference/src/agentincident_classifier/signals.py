"""Signal extraction from traces and constraints."""

from __future__ import annotations

from typing import Any


def extract_error_signals(trace: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Scan trace outputs for error patterns.

    Returns a list of dicts with keys: seq, tool, error_type, detail.
    """
    signals = []
    error_keys = {"error", "exception", "error_message", "error_code"}
    error_statuses = {"failed", "failure", "error"}

    for entry in trace:
        output = entry.get("output", {})
        if not isinstance(output, dict):
            continue

        # Check for error keys in output
        for key in error_keys:
            if key in output:
                signals.append({
                    "seq": entry.get("seq"),
                    "tool": entry.get("tool"),
                    "error_type": "error_key",
                    "detail": f"{key}={output[key]}",
                })
                break

        # Check for HTTP error status codes
        status = output.get("status") or output.get("status_code") or output.get("http_status")
        if status is not None:
            status_str = str(status)
            if status_str.startswith(("4", "5")) and status_str.isdigit() and len(status_str) == 3:
                signals.append({
                    "seq": entry.get("seq"),
                    "tool": entry.get("tool"),
                    "error_type": "http_error",
                    "detail": f"status={status}",
                })
            elif status_str.lower() in error_statuses:
                signals.append({
                    "seq": entry.get("seq"),
                    "tool": entry.get("tool"),
                    "error_type": "status_error",
                    "detail": f"status={status}",
                })

    return signals


def extract_constraint_signals(constraints: list[dict[str, Any]]) -> dict[str, Any]:
    """Summarize constraint pass/fail status.

    Returns dict with keys: total, passed, failed, failed_policies, has_gaps, gaps.
    """
    total = len(constraints)
    passed = 0
    failed = 0
    failed_policies = []
    all_gaps: list[str] = []

    for c in constraints:
        result = c.get("eval_result", "")
        if result == "pass":
            passed += 1
        elif result == "fail":
            failed += 1
            failed_policies.append(c.get("policy", "unknown"))

        gaps = c.get("gaps_identified", [])
        if isinstance(gaps, list):
            all_gaps.extend(gaps)

    return {
        "total": total,
        "passed": passed,
        "failed": failed,
        "failed_policies": failed_policies,
        "has_gaps": len(all_gaps) > 0,
        "gaps": all_gaps,
    }


def extract_irreversible_actions(trace: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return trace entries where irreversible is True."""
    return [
        {"seq": e.get("seq"), "tool": e.get("tool"), "ts": e.get("ts")}
        for e in trace
        if e.get("irreversible") is True
    ]


def extract_timing_anomalies(trace: list[dict[str, Any]], threshold_ms: int = 30000) -> list[dict[str, Any]]:
    """Return entries with unusual duration_ms (above threshold).

    Also detects timeout-like patterns in output text.
    """
    anomalies = []
    for entry in trace:
        duration = entry.get("duration_ms")
        if duration is not None and duration > threshold_ms:
            anomalies.append({
                "seq": entry.get("seq"),
                "tool": entry.get("tool"),
                "duration_ms": duration,
                "reason": "high_duration",
            })
            continue

        # Check for timeout keywords in output
        output = entry.get("output", {})
        if isinstance(output, dict):
            output_str = str(output).lower()
            if "timeout" in output_str or "timed out" in output_str:
                anomalies.append({
                    "seq": entry.get("seq"),
                    "tool": entry.get("tool"),
                    "duration_ms": duration,
                    "reason": "timeout_in_output",
                })

    return anomalies
