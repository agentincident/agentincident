"""Reference rules-based classifier for AgentIncident records."""

from __future__ import annotations

from .rules import classify, ClassificationResult

__all__ = ["classify", "ClassificationResult"]
