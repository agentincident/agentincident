from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_SCHEMA_PATH = Path(__file__).parent / "schema" / "v0.1.json"
_schema_cache: dict[str, Any] | None = None


def get_schema() -> dict[str, Any]:
    """Return the bundled JSON schema as a dict."""
    global _schema_cache
    if _schema_cache is None:
        _schema_cache = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
    return _schema_cache


def validate(data: dict[str, Any] | object, level: str = "core") -> list[str]:
    """Validate data against the AgentIncident schema.

    Args:
        data: A dict or an Incident object. If an Incident, it will be
              converted to dict first.
        level: Conformance level - "core", "standard", or "full".

    Returns:
        List of error messages. Empty list means valid.

    Raises:
        ImportError: If jsonschema is not installed.
    """
    try:
        import jsonschema
    except ImportError:
        raise ImportError(
            "jsonschema is required for validation. "
            "Install with: pip install agentincident[validation]"
        )

    # Convert Incident objects to dict
    from .types import Incident
    if isinstance(data, Incident):
        from .export import incident_to_dict
        data = incident_to_dict(data)

    schema = get_schema()

    # Build a validation schema based on conformance level.
    # Standard and Full defs use allOf with $ref:"#" which causes recursion,
    # so we flatten the extra requirements into the root schema manually.
    if level == "core":
        validate_schema = schema
    elif level == "standard":
        # Core + meta, classification, loss_estimate required
        validate_schema = _merge_level(schema, schema["$defs"]["StandardRecord"])
    elif level == "full":
        validate_schema = _merge_level(schema, schema["$defs"]["FullRecord"])
    else:
        return [f"Unknown validation level: {level}"]

    from referencing import Registry, Resource
    resource = Resource.from_contents(schema)
    registry = Registry().with_resource(schema.get("$id", ""), resource)
    validator = jsonschema.Draft202012Validator(validate_schema, registry=registry)

    errors: list[str] = []
    for error in validator.iter_errors(data):
        errors.append(error.message)
    return errors


def _merge_level(root_schema: dict[str, Any], level_def: dict[str, Any]) -> dict[str, Any]:
    """Flatten a conformance level definition into a standalone schema.

    The level defs use allOf with $ref:"#" which causes recursion.
    We resolve this by copying the root schema and adding extra
    required fields from the level definition.
    """
    import copy
    merged = copy.deepcopy(root_schema)
    # Remove $defs from merged to avoid confusion (keep them for $ref resolution)
    for item in level_def.get("allOf", []):
        if "$ref" in item:
            continue  # Skip self-reference
        # Merge required fields
        if "required" in item:
            existing = set(merged.get("required", []))
            existing.update(item["required"])
            merged["required"] = sorted(existing)
        # Merge property-level constraints (e.g., full requires response sub-fields)
        if "properties" in item:
            for prop_name, prop_constraints in item["properties"].items():
                if prop_name in merged.get("properties", {}):
                    prop = merged["properties"][prop_name]
                    if "required" in prop_constraints:
                        prop = dict(prop)
                        prop["required"] = prop_constraints["required"]
                        merged["properties"][prop_name] = prop
    return merged
