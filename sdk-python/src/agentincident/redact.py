from __future__ import annotations

import copy
import re
from typing import Any

from .hash import compute_hash
from .types import Incident

# Default PII patterns
_DEFAULT_PATTERNS: list[re.Pattern[str]] = [
    # Email addresses
    re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"),
    # Credit card numbers (basic: 13-19 digits, possibly with spaces/dashes)
    re.compile(r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{1,7}\b"),
    # API keys starting with sk- or sk_
    re.compile(r"\bsk[-_][a-zA-Z0-9]{20,}\b"),
    # Bearer tokens
    re.compile(r"\bBearer\s+[a-zA-Z0-9_.~+/=-]+\b"),
]

REDACTED = "[REDACTED]"


def _redact_value(value: Any, patterns: list[re.Pattern[str]], fields: set[str] | None) -> Any:
    """Recursively redact values matching patterns or field names."""
    if isinstance(value, str):
        result = value
        for pattern in patterns:
            result = pattern.sub(REDACTED, result)
        return result
    elif isinstance(value, dict):
        return {
            k: REDACTED if (fields and k in fields) else _redact_value(v, patterns, fields)
            for k, v in value.items()
        }
    elif isinstance(value, list):
        return [_redact_value(item, patterns, fields) for item in value]
    return value


def redact_incident(
    incident: Incident,
    patterns: list[re.Pattern[str]] | None = None,
    fields: list[str] | None = None,
) -> Incident:
    """Return a new Incident with PII redacted from trace inputs/outputs.

    Default patterns match: email addresses, credit card numbers,
    API keys (sk-*), and Bearer tokens.

    Matched values are replaced with '[REDACTED]'. Hashes are recomputed
    after redaction.

    Args:
        incident: The incident to redact.
        patterns: Custom regex patterns. If None, uses defaults.
        fields: Field names whose values should be fully redacted.

    Returns:
        A new Incident with redacted trace entries and recomputed hashes.
    """
    redact_patterns = patterns if patterns is not None else _DEFAULT_PATTERNS
    field_set = set(fields) if fields else None

    new_incident = copy.deepcopy(incident)

    for entry in new_incident.trace:
        entry.input = _redact_value(entry.input, redact_patterns, field_set)
        entry.output = _redact_value(entry.output, redact_patterns, field_set)
        entry.hash = compute_hash(entry.input, entry.output)

    return new_incident
