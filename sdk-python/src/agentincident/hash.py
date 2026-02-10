from __future__ import annotations

import hashlib
import json
from typing import Any


def compute_hash(input: dict[str, Any], output: dict[str, Any]) -> str:
    """Compute a deterministic SHA-256 hash of input + output.

    Canonicalization: json.dumps with sort_keys=True, compact separators,
    and default=str for non-serializable types.

    Returns: "sha256:<hex>"
    """
    canonical = json.dumps(
        {"input": input, "output": output},
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"
