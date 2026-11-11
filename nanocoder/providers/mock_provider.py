"""Mock LLM Provider for deterministic offline testing and benchmark demos."""

from typing import Optional, List, Dict
import re
from nanocoder.providers.base import BaseProvider
from nanocoder.telemetry.token_counter import TokenUsage, estimate_tokens


class MockProvider(BaseProvider):
    """Simulates an ultra-precise, token-thrifty coding agent.
    
    Provides authentic step-by-step reasoning for benchmark tasks
    with zero API key requirements.
    """

    def __init__(self, token_usage: TokenUsage):
        super().__init__(token_usage)
        self.step_counter = 0

    def generate(self, prompt: str) -> str:
        # Extract the current step number from prompt
        m = re.search(r'### Step (\d+):', prompt)
        current_step = int(m.group(1)) if m else (self.step_counter + 1)
        self.step_counter = current_step

        # Check prompt context to decide on realistic next step
        prompt_lower = prompt.lower()

        # Task 1: Calculator ZeroDivisionError / Bug fix
        if "calculator" in prompt_lower or "zerodivision" in prompt_lower or "divide" in prompt_lower:
            return self._handle_calculator_task(current_step)

        # Task 2: Auth login / Token validation refactor
        if "auth" in prompt_lower or "login" in prompt_lower:
            return self._handle_auth_task(current_step)

        # General fallback: test execution or inspection
        return self._handle_general_task(current_step)

    def _handle_calculator_task(self, step: int) -> str:
        if step == 1:
            return """THOUGHT: I need to inspect calculator.py to see where the divide function is defined and why ZeroDivisionError isn't handled gracefully.
ACTION: read_skeleton(file_path="app/calculator.py")"""

        elif step == 2:
            return """THOUGHT: In the skeleton, divide() is located at lines 20-32. Let's read those exact lines.
ACTION: read_snippet(file_path="app/calculator.py", start_line=20, end_line=32)"""

        elif step == 3:
            return """THOUGHT: Line 26 has `return a / b` without checking if b == 0. Let's run the test suite to verify the exact failure.
ACTION: run_command(command="pytest tests/test_calculator.py")"""

        elif step == 4:
            return """THOUGHT: The test confirms ZeroDivisionError when b == 0, expecting ValueError("Division by zero is undefined"). Let's apply a surgical patch.
ACTION: search_replace_patch(file_path="app/calculator.py", search_block='''    if b == 0:
        return a / b  # BUG: Causes ZeroDivisionError rather than expected ValueError''', replace_block='''    if b == 0:
        raise ValueError("Division by zero is undefined")''')"""

        elif step == 5:
            return """THOUGHT: Now that the surgical patch is applied, let's run pytest to confirm all tests pass.
ACTION: run_command(command="pytest tests/test_calculator.py")"""

        else:
            return """THOUGHT: All unit tests are passing and the fix is verified with minimal token overhead.
COMPLETE: Successfully patched ZeroDivisionError handling in calculator.py and confirmed all unit tests pass."""

    def _handle_auth_task(self, step: int) -> str:
        if step == 1:
            return """THOUGHT: Let's read the skeleton of auth.py to locate token validation logic.
ACTION: read_skeleton(file_path="app/auth.py")"""
        elif step == 2:
            return """THOUGHT: Reading snippet of verify_token method around line 15.
ACTION: read_snippet(file_path="app/auth.py", start_line=12, end_line=25)"""
        elif step == 3:
            return """THOUGHT: Applying patch to check expiration and validate token.
ACTION: search_replace_patch(file_path="app/auth.py", search_block='''    def verify_token(self, token: Optional[str]) -> bool:
        \"\"\"Verifies if the provided session token is valid and active.\"\"\"
        if not token:
            return False
        return token in self.active_sessions''', replace_block='''    def verify_token(self, token: Optional[str]) -> bool:
        \"\"\"Verifies if the provided session token is valid and active.\"\"\"
        if not token or token.strip() == "":
            return False
        return token in self.active_sessions''')"""
        elif step == 4:
            return """THOUGHT: Running test suite to confirm auth verification.
ACTION: run_command(command="pytest tests/test_auth.py")"""
        else:
            return """THOUGHT: Auth token verification logic fixed and verified.
COMPLETE: Successfully refactored token verification."""

    def _handle_general_task(self, step: int) -> str:
        if step == 1:
            return """THOUGHT: Let's check the test suite first to isolate any existing failures.
ACTION: run_command(command="pytest")"""
        else:
            return """THOUGHT: Task objectives are satisfied.
COMPLETE: Diagnostic run completed and system verified."""
