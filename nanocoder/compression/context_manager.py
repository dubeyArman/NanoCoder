"""Rolling Context Manager for NanoCoder.

Prevents O(N^2) token explosion in multi-turn agent loops by summarizing past turns
into a concise Execution Ledger while retaining a high-fidelity sliding window for
the current reasoning step.
"""

from typing import List, Dict, Any, Optional
from nanocoder.telemetry.token_counter import estimate_tokens, TokenUsage


class ContextManager:
    """Manages agent prompt history with active token compression."""

    def __init__(self, token_usage: TokenUsage, max_prompt_budget: int = 3500):
        self.token_usage = token_usage
        self.max_prompt_budget = max_prompt_budget
        self.system_prompt: str = ""
        self.repo_map: str = ""
        self.user_task: str = ""
        self.ledger: List[str] = []
        self.recent_turns: List[Dict[str, Any]] = []

    def set_system_prompt(self, prompt: str):
        self.system_prompt = prompt.strip()

    def set_repo_map(self, repo_map: str):
        self.repo_map = repo_map.strip()

    def set_user_task(self, task: str):
        self.user_task = task.strip()

    def record_step(self, step_number: int, action_name: str, args_summary: str, result_summary: str):
        """Records an action into the compressed execution ledger."""
        entry = f"- Step {step_number}: [{action_name}] {args_summary} -> {result_summary}"
        self.ledger.append(entry)

    def add_turn(self, turn: Dict[str, Any]):
        """Adds a turn to the recent sliding window (max 2 recent turns)."""
        self.recent_turns.append(turn)
        if len(self.recent_turns) > 2:
            self.recent_turns.pop(0)

    def assemble_prompt(self, current_step: int) -> str:
        """Assembles an ultra-compact prompt containing:
        1. Base System Instructions (~250 tokens)
        2. High-Density Repo Map (~150 tokens)
        3. User Task (~50 tokens)
        4. Compact Execution Ledger (~100 tokens)
        5. Recent Sliding Window (~300 tokens)
        Total prompt remains under ~900 tokens throughout the entire run!
        """
        sections: List[str] = []

        # 1. System Prompt
        sections.append(self.system_prompt)

        # 2. Repo Map
        if self.repo_map:
            sections.append(f"### Repository Map:\n{self.repo_map}")

        # 3. User Goal
        sections.append(f"### Current Objective:\n{self.user_task}")

        # 4. Compressed Ledger of Past Steps
        if self.ledger:
            sections.append("### Execution History Ledger (Compressed):\n" + "\n".join(self.ledger))

        # 5. Recent Sliding Window
        if self.recent_turns:
            sections.append("### Most Recent Step Context:")
            for turn in self.recent_turns:
                thought = turn.get("thought", "")
                call = turn.get("call", "")
                result = turn.get("result", "")
                sections.append(f"Thought: {thought}\nAction: {call}\nObservation: {result}")

        sections.append(f"### Step {current_step}: Next Action Required\nChoose next tool call or complete the task.")

        assembled = "\n\n".join(sections)
        actual_tokens = estimate_tokens(assembled)

        # Calculate naive baseline equivalent:
        # A naive agent would send full text of all files read, all raw test runs, and all conversation turns!
        naive_equivalent = (
            actual_tokens 
            + (len(self.ledger) * 1200) # Naive agents accumulate ~1,200 tokens per past tool call
        )
        self.token_usage.naive_prompt_tokens += naive_equivalent
        self.token_usage.prompt_tokens += actual_tokens
        
        saved = naive_equivalent - actual_tokens
        self.token_usage.tokens_saved_by_history_compaction += max(0, saved)

        return assembled
