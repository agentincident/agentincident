"""Tests for LangChain integration (mock-based)."""
from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from agentincident import Recorder


class TestLangChainCallbackHandler:
    @pytest.fixture(autouse=True)
    def setup_mock(self):
        """Mock langchain_core so we can test without the dependency."""
        mock_module = MagicMock()

        class FakeBaseCallbackHandler:
            def __init__(self):
                pass

        mock_module.BaseCallbackHandler = FakeBaseCallbackHandler
        with patch.dict(
            "sys.modules",
            {"langchain_core": MagicMock(), "langchain_core.callbacks": mock_module},
        ):
            # Re-import to pick up mocked module
            import importlib
            import agentincident.integrations._langchain as lc_mod

            importlib.reload(lc_mod)
            self.lc_mod = lc_mod
            yield

    def test_tool_start_and_end(self):
        rec = Recorder()
        handler = self.lc_mod.AgentIncidentCallbackHandler(rec)

        run_id = uuid4()
        handler.on_tool_start(
            serialized={"name": "search"},
            input_str="query=test",
            run_id=run_id,
        )
        handler.on_tool_end(output="result data", run_id=run_id)

        assert len(rec.entries) == 1
        assert rec.entries[0].tool == "search"
        assert rec.entries[0].input == {"input": "query=test"}
        assert rec.entries[0].output == {"output": "result data"}

    def test_tool_error(self):
        rec = Recorder()
        handler = self.lc_mod.AgentIncidentCallbackHandler(rec)

        run_id = uuid4()
        handler.on_tool_start(
            serialized={"name": "failing_tool"},
            input_str="bad input",
            run_id=run_id,
        )
        handler.on_tool_error(error=RuntimeError("fail"), run_id=run_id)

        assert len(rec.entries) == 1
        assert rec.entries[0].tool == "failing_tool"
        assert "fail" in rec.entries[0].output["error"]

    def test_end_without_start_ignored(self):
        rec = Recorder()
        handler = self.lc_mod.AgentIncidentCallbackHandler(rec)
        handler.on_tool_end(output="orphan", run_id=uuid4())
        assert len(rec.entries) == 0

    def test_multiple_concurrent_tools(self):
        rec = Recorder()
        handler = self.lc_mod.AgentIncidentCallbackHandler(rec)

        id1 = uuid4()
        id2 = uuid4()
        handler.on_tool_start(serialized={"name": "tool1"}, input_str="a", run_id=id1)
        handler.on_tool_start(serialized={"name": "tool2"}, input_str="b", run_id=id2)
        handler.on_tool_end(output="result2", run_id=id2)
        handler.on_tool_end(output="result1", run_id=id1)

        assert len(rec.entries) == 2
        assert rec.entries[0].tool == "tool2"
        assert rec.entries[1].tool == "tool1"
