"""Tests for OpenAI Agents SDK integration (mock-based)."""
from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch

import pytest

from agentincident import Recorder


class TestOpenAIAgentsHooks:
    @pytest.fixture(autouse=True)
    def setup_mock(self):
        """Mock the agents module so we can test without the dependency."""
        mock_agents = MagicMock()

        class FakeRunHooks:
            pass

        mock_agents.RunHooks = FakeRunHooks
        with patch.dict("sys.modules", {"agents": mock_agents}):
            import importlib
            import agentincident.integrations._openai_agents as oai_mod

            importlib.reload(oai_mod)
            self.oai_mod = oai_mod
            yield

    def test_tool_start_and_end(self):
        rec = Recorder()
        hooks = self.oai_mod.AgentIncidentRunHooks(rec)

        tool = MagicMock()
        tool.name = "web_search"
        tool.input = {"query": "test"}

        context = MagicMock()
        agent = MagicMock()

        asyncio.run(hooks.on_tool_start(context, agent, tool))
        asyncio.run(hooks.on_tool_end(context, agent, tool, {"results": ["a", "b"]}))

        assert len(rec.entries) == 1
        assert rec.entries[0].tool == "web_search"
        assert rec.entries[0].input == {"query": "test"}
        assert rec.entries[0].output == {"results": ["a", "b"]}

    def test_non_dict_result(self):
        rec = Recorder()
        hooks = self.oai_mod.AgentIncidentRunHooks(rec)

        tool = MagicMock()
        tool.name = "calculator"
        tool.input = {"expr": "2+2"}

        context = MagicMock()
        agent = MagicMock()

        asyncio.run(hooks.on_tool_start(context, agent, tool))
        asyncio.run(hooks.on_tool_end(context, agent, tool, "4"))

        assert rec.entries[0].output == {"result": "4"}

    def test_end_without_start(self):
        rec = Recorder()
        hooks = self.oai_mod.AgentIncidentRunHooks(rec)

        tool = MagicMock()
        tool.name = "orphan"
        tool.input = {}

        context = MagicMock()
        agent = MagicMock()

        asyncio.run(hooks.on_tool_end(context, agent, tool, {"ok": True}))
        # Should still record (with empty input from missing pending)
        assert len(rec.entries) == 1
