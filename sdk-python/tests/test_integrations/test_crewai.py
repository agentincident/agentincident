"""Tests for CrewAI integration (mock-based)."""
from __future__ import annotations

from unittest.mock import MagicMock

from agentincident import Recorder
from agentincident.integrations._crewai import crewai_step_callback


class TestCrewAIStepCallback:
    def test_basic_step(self):
        rec = Recorder()
        callback = crewai_step_callback(rec)

        step = MagicMock()
        step.tool = "search_tool"
        step.tool_input = {"query": "test"}
        step.observation = "Found results"

        callback(step)

        assert len(rec.entries) == 1
        assert rec.entries[0].tool == "search_tool"
        assert rec.entries[0].input == {"query": "test"}
        assert rec.entries[0].output == {"output": "Found results"}

    def test_dict_observation(self):
        rec = Recorder()
        callback = crewai_step_callback(rec)

        step = MagicMock()
        step.tool = "api_call"
        step.tool_input = {"url": "https://api.example.com"}
        step.observation = {"status": 200, "body": "ok"}

        callback(step)

        assert rec.entries[0].output == {"status": 200, "body": "ok"}

    def test_non_dict_input(self):
        rec = Recorder()
        callback = crewai_step_callback(rec)

        step = MagicMock()
        step.tool = "simple"
        step.tool_input = "just a string"
        step.observation = "result"

        callback(step)

        assert rec.entries[0].input == {"input": "just a string"}

    def test_multiple_steps(self):
        rec = Recorder()
        callback = crewai_step_callback(rec)

        for i in range(3):
            step = MagicMock()
            step.tool = f"tool_{i}"
            step.tool_input = {"i": i}
            step.observation = f"result_{i}"
            callback(step)

        assert len(rec.entries) == 3
        assert rec.entries[0].seq == 1
        assert rec.entries[2].seq == 3
