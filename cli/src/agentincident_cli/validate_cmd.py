"""Schema validation command."""

from __future__ import annotations

import json
import sys
from typing import Any


def validate_file(file_path: str, level: str = "core") -> tuple[bool, list[str]]:
    """Validate a JSON file against the AgentIncident schema.

    Returns (is_valid, errors).
    """
    try:
        if file_path == "-":
            data = json.load(sys.stdin)
        else:
            with open(file_path) as f:
                data = json.load(f)
    except json.JSONDecodeError as e:
        return False, [f"Invalid JSON: {e}"]
    except FileNotFoundError:
        return False, [f"File not found: {file_path}"]

    try:
        from agentincident.schema import validate
        errors = validate(data, level=level)
        return len(errors) == 0, errors
    except ImportError:
        return False, ["agentincident[validation] is required for validation. Install with: pip install agentincident[validation]"]


def print_schema() -> None:
    """Print the JSON schema to stdout."""
    from agentincident.schema import get_schema
    print(json.dumps(get_schema(), indent=2))
