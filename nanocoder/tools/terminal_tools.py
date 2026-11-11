"""Terminal command execution with automatic output distillation."""

import subprocess
import os
from typing import Tuple, Dict, Any
from nanocoder.compression.output_distiller import OutputDistiller
from nanocoder.telemetry.token_counter import estimate_tokens, TokenUsage


class TerminalTools:
    """Executes workspace commands with output distillation."""

    def __init__(self, workspace_root: str, token_usage: TokenUsage):
        self.workspace_root = os.path.abspath(workspace_root)
        self.token_usage = token_usage

    def run_command(self, command: str, timeout_seconds: int = 45) -> str:
        """Executes a terminal command and returns a distilled, token-thrifty output."""
        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=self.workspace_root,
                capture_output=True,
                text=True,
                timeout=timeout_seconds
            )
            raw_stdout = result.stdout or ""
            raw_stderr = result.stderr or ""
            combined = raw_stdout + ("\nSTDERR:\n" + raw_stderr if raw_stderr else "")
            exit_code = result.returncode
        except subprocess.TimeoutExpired:
            return f"[Error: Command '{command}' timed out after {timeout_seconds}s]"
        except Exception as e:
            return f"[Error executing '{command}': {str(e)}]"

        # Distill output
        distilled, raw_tokens, distilled_tokens = OutputDistiller.distill_generic_terminal(
            command, combined, exit_code
        )

        # Track token savings: Naive agents pass raw stdout/stderr into context verbatim
        saved = max(0, raw_tokens - distilled_tokens)
        self.token_usage.tokens_saved_by_distillation += saved

        return distilled
