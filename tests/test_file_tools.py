"""Tests for surgical file manipulation tools."""

import pytest
import os
import tempfile
from nanocoder.tools.file_tools import FileTools
from nanocoder.telemetry.token_counter import TokenUsage


def test_search_replace_patch():
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "math_module.py")
        original_code = "def divide(a, b):\n    return a / b\n"
        with open(test_file, "w") as f:
            f.write(original_code)

        usage = TokenUsage()
        tools = FileTools(tmpdir, usage)
        
        result = tools.search_replace_patch(
            "math_module.py",
            search_block="    return a / b",
            replace_block="    if b == 0:\n        raise ValueError('Zero')\n    return a / b"
        )

        assert "Patch successfully applied" in result
        
        with open(test_file, "r") as f:
            updated = f.read()
            
        assert "raise ValueError('Zero')" in updated
        assert usage.tokens_saved_by_surgical_patch > 0


def test_read_snippet():
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "data.txt")
        lines = [f"Line {i}\n" for i in range(1, 51)]
        with open(test_file, "w") as f:
            f.writelines(lines)

        usage = TokenUsage()
        tools = FileTools(tmpdir, usage)
        snippet = tools.read_snippet("data.txt", 10, 15)

        assert "Line 10" in snippet
        assert "Line 15" in snippet
        assert "Line 1\n" not in snippet
        assert "Line 45" not in snippet
