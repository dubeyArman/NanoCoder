"""Output Distiller for compressing terminal outputs, test runs, and tracebacks.

Filters out noise, boilerplate, passing test suites, and redundant frames to extract
only the high-value diagnostic failure points. Cuts tool feedback tokens by 80-95%.
"""

import re
from typing import Tuple, List
from nanocoder.telemetry.token_counter import estimate_tokens


class OutputDistiller:
    """Compresses verbose terminal and test outputs into distilled actionable tokens."""

    @staticmethod
    def strip_ansi(text: str) -> str:
        """Removes ANSI color codes and escape sequences."""
        ansi_regex = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        return ansi_regex.sub('', text)

    @classmethod
    def distill_pytest_output(cls, raw_output: str) -> Tuple[str, int, int]:
        """Compresses pytest test runner output into compact failure diagnostics."""
        clean = cls.strip_ansi(raw_output)
        raw_tokens = estimate_tokens(clean)
        lines = clean.splitlines()

        # Check for clean success
        if "passed" in clean and ("failed" not in clean and "ERROR" not in clean):
            summary_match = re.search(r'(=+\s*[\d\w\s,]+in\s+[\d\.]+s\s*=+|[\d]+\s+passed)', clean)
            summary = summary_match.group(0) if summary_match else "All tests passed successfully."
            distilled = f"[TEST SUCCESS] {summary.strip(' =')}"
            return distilled, raw_tokens, estimate_tokens(distilled)

        # Distill failures
        distilled_lines: List[str] = ["[TEST RUNNER: FAILURES DETECTED]"]
        in_failure_block = False
        captured_frames = 0
        
        for line in lines:
            line_str = line.strip()
            
            # Detect failure header
            if line_str.startswith("___") and line_str.endswith("___"):
                distilled_lines.append(f"\nFailure in: {line_str.strip('_ ')}")
                in_failure_block = True
                captured_frames = 0
                continue
            
            if in_failure_block:
                # Capture file location & assertion line
                if re.search(r'(\.py:\d+:|in test_|E\s+|AssertionError|TypeError|ValueError|IndexError|AttributeError)', line):
                    # Clean pytest prefix
                    cleaned_line = line.replace("E   ", "--> ")
                    distilled_lines.append(cleaned_line)
                    captured_frames += 1
                elif line_str.startswith("def test_"):
                    distilled_lines.append(f"  {line_str}")
                elif "short test summary info" in line.lower() or line_str.startswith("===="):
                    in_failure_block = False

        # Capture final summary line (e.g. "= 1 failed, 3 passed in 0.05s =")
        summary_line = next((l for l in reversed(lines) if "failed" in l and ("passed" in l or "in " in l)), None)
        if summary_line:
            distilled_lines.append(f"\nSummary: {summary_line.strip(' =')}")

        if len(distilled_lines) <= 2:
            # Fallback if specific pytest blocks not matched: keep top 20 lines with errors
            distilled_lines = [l for l in lines if any(k in l.lower() for k in ["fail", "error", "assert", "traceback", "line "])][:20]

        distilled_text = "\n".join(distilled_lines).strip()
        distilled_tokens = estimate_tokens(distilled_text)
        return distilled_text, raw_tokens, distilled_tokens

    @classmethod
    def distill_generic_terminal(cls, command: str, raw_output: str, exit_code: int = 0) -> Tuple[str, int, int]:
        """Distills general command line output based on command type."""
        clean = cls.strip_ansi(raw_output)
        raw_tokens = estimate_tokens(clean)
        lines = [l for l in clean.splitlines() if l.strip()]

        if not lines:
            msg = f"[Command '{command}' completed with exit code {exit_code} (No output)]"
            return msg, raw_tokens, estimate_tokens(msg)

        # If it's a test command
        if any(tool in command.lower() for tool in ["pytest", "unittest", "test"]):
            return cls.distill_pytest_output(raw_output)

        # If short output (< 15 lines), keep as is
        if len(lines) <= 15:
            distilled = f"[Exit code {exit_code}]\n" + "\n".join(lines)
            return distilled, raw_tokens, estimate_tokens(distilled)

        # For long outputs, keep first 6 lines, lines with error/warning, and last 4 lines
        head = lines[:6]
        tail = lines[-4:]
        important_middle = [
            l for l in lines[6:-4] 
            if any(k in l.lower() for k in ["error", "fail", "fatal", "warn", "exception"])
        ][:10]

        condensed = [f"[Exit code {exit_code}]"] + head
        if important_middle:
            condensed.append(f"... [{len(lines) - 10} lines collapsed, key notices below] ...")
            condensed.extend(important_middle)
        else:
            condensed.append(f"... [Truncated {len(lines) - 10} lines of routine output] ...")
        condensed.extend(tail)

        distilled_text = "\n".join(condensed)
        distilled_tokens = estimate_tokens(distilled_text)
        return distilled_text, raw_tokens, distilled_tokens
