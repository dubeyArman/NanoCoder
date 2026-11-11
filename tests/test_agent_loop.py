"""End-to-end integration test of NanoCoderAgent."""

import pytest
import os
import shutil
import tempfile
from nanocoder.agent import NanoCoderAgent
from nanocoder.providers.mock_provider import MockProvider


def test_agent_end_to_end_bugfix():
    # Setup isolated test workspace copying demo_workspace
    source_workspace = os.path.abspath("demo_workspace")
    with tempfile.TemporaryDirectory() as tmp_workspace:
        shutil.copytree(os.path.join(source_workspace, "app"), os.path.join(tmp_workspace, "app"))
        shutil.copytree(os.path.join(source_workspace, "tests"), os.path.join(tmp_workspace, "tests"))

        # Initialize NanoCoder agent with MockProvider (deterministic benchmark mode)
        agent = NanoCoderAgent(workspace_root=tmp_workspace)
        
        result = agent.solve("Fix ZeroDivisionError in app/calculator.py divide function to raise ValueError('Division by zero is undefined')")

        assert result["status"] == "completed"
        assert result["steps"] >= 3
        
        # Verify telemetry
        telemetry = result["telemetry"]
        assert telemetry["total_tokens"] > 0
        assert telemetry["naive_total_tokens"] > telemetry["total_tokens"]
        assert float(telemetry["percentage_saved"].replace("%", "")) > 70.0

        # Verify that the fix was actually written and tests now pass in tmp_workspace!
        from nanocoder.tools.terminal_tools import TerminalTools
        terminal = TerminalTools(tmp_workspace, agent.token_usage)
        test_run = terminal.run_command("pytest tests/test_calculator.py")
        assert "SUCCESS" in test_run or "passed" in test_run.lower()
